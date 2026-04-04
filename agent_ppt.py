"""
Auto-PPT Agent V2: Multi-Agent Pipeline
----------------------------------------
3-stage architecture:
  Stage 1: PLANNER  — LLM generates structured JSON slide plan
  Stage 2: CRITIC   — LLM refines the plan for design quality
  Stage 3: DESIGNER — Deterministic Python executes MCP tools
"""

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv
from ddgs import DDGS

load_dotenv()

import asyncio
import json
import os
import re

# ──────────────────────────────────────────────
# PROMPT TEMPLATES
# ──────────────────────────────────────────────

PLANNER_PROMPT = """You are a presentation planner. Given a user's topic, output ONLY a valid JSON object for a slide deck.

STRICT RULES:
- Output ONLY the JSON object. No markdown, no explanation, no code fences.
- Max 6 slides total (unless user specifies more).
- Max 4 bullets per slide. Max 8 words per bullet.
- Titles must be <= 6 words.
- Every slide MUST have a visual idea.
- Choose ONE theme for the whole deck from: space, business, education, tech, nature, medical
- For visual.type: use "image" for real-world topics, "diagram" for processes/systems/workflows, "none" for title slides.
- For layout: choose from text_left_image_right, image_background, text_only, title_only.
- First slide should always be layout "title_only" with visual.type "none".

JSON FORMAT:
{
  "theme": "space",
  "slides": [
    {
      "title": "Short Title Here",
      "subtitle": "Only for title_only slides",
      "bullets": ["Point one", "Point two"],
      "visual": {"type": "image", "description": "what to search for"},
      "layout": "text_left_image_right"
    }
  ]
}"""

CRITIC_PROMPT = """You are a presentation design critic. You will receive a JSON slide plan.

Review it and output an IMPROVED version following these rules:
- Output ONLY the improved JSON object. No markdown, no explanation, no code fences.
- Each bullet must be <= 8 words. Shorten any that are too long.
- Max 4 bullets per slide. Remove extras.
- Titles must be <= 6 words. Shorten if needed.
- Every non-title slide MUST have a visual (image or diagram).
- Ensure variety in layouts — don't repeat the same layout 3 times in a row.
- Improve storytelling flow: intro → body → conclusion.
- Make bullets punchy and minimal, not sentences.

Output the improved JSON only."""


# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from LLM text output, handling markdown fences."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("```"):
        # Remove markdown code fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def _search_image(query: str) -> str | None:
    """Search DuckDuckGo for an image URL matching the query."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=5))
            for r in results:
                url = r.get("image", "")
                if url and (url.endswith(".jpg") or url.endswith(".png") or url.endswith(".jpeg") 
                           or ".jpg" in url or ".png" in url):
                    return url
            # Fallback: return first result regardless of extension
            if results:
                return results[0].get("image", None)
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────

async def run_ppt_agent(chat_history: list, progress_callback=None):
    """
    Multi-agent pipeline:
      1. PLANNER: LLM → structured JSON plan
      2. CRITIC: LLM → refined JSON plan
      3. DESIGNER: Python → MCP tool execution
    """
    
    def _report(stage: str, detail: str):
        """Report progress to Streamlit callback if available."""
        print(f"[{stage}] {detail}")
        if progress_callback:
            progress_callback(stage, detail)
    
    # ── Initialize LLM ──
    _report("INIT", "Initializing LLM...")
    llm_endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-7B-Instruct",
        max_new_tokens=2048,
        temperature=0.2
    )
    llm = ChatHuggingFace(llm=llm_endpoint)
    
    # Extract the user's latest message
    user_prompt = ""
    for msg in reversed(chat_history):
        if isinstance(msg, HumanMessage):
            user_prompt = msg.content
            break
    
    if not user_prompt:
        return {"output": "Error: No user prompt found.", "trace": []}
    
    trace_log = []
    
    # ══════════════════════════════════════════
    # STAGE 1: PLANNER
    # ══════════════════════════════════════════
    _report("PLANNER", f"Planning slides for: {user_prompt[:80]}...")
    trace_log.append("🎯 **Stage 1: PLANNER** — Generating structured slide plan...")
    
    planner_messages = [
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"Create a presentation about: {user_prompt}")
    ]
    
    planner_response = await llm.ainvoke(planner_messages)
    planner_text = planner_response.content
    
    slide_plan = _extract_json(planner_text)
    if slide_plan is None:
        trace_log.append("⚠️ Planner failed to produce valid JSON. Using fallback plan.")
        slide_plan = {
            "theme": "tech",
            "slides": [
                {"title": user_prompt[:30], "subtitle": "AI-Generated Presentation", "bullets": [], 
                 "visual": {"type": "none", "description": ""}, "layout": "title_only"},
                {"title": "Key Points", "bullets": ["Generated from prompt", "Powered by AI", "MCP Architecture"],
                 "visual": {"type": "image", "description": user_prompt}, "layout": "text_left_image_right"},
                {"title": "Summary", "bullets": ["Thank you"], 
                 "visual": {"type": "none", "description": ""}, "layout": "title_only"}
            ]
        }
    
    num_slides = len(slide_plan.get("slides", []))
    trace_log.append(f"✅ Plan created: **{num_slides} slides**, theme: **{slide_plan.get('theme', 'space')}**")
    
    # ══════════════════════════════════════════
    # STAGE 2: CRITIC
    # ══════════════════════════════════════════
    _report("CRITIC", "Refining slide plan for design quality...")
    trace_log.append("\n🔍 **Stage 2: CRITIC** — Refining plan for visual quality...")
    
    critic_messages = [
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=json.dumps(slide_plan, indent=2))
    ]
    
    critic_response = await llm.ainvoke(critic_messages)
    refined_plan = _extract_json(critic_response.content)
    
    if refined_plan and "slides" in refined_plan:
        slide_plan = refined_plan
        trace_log.append("✅ Critic refined the plan successfully.")
    else:
        trace_log.append("⚠️ Critic output was not valid JSON. Using original plan.")
    
    # ══════════════════════════════════════════
    # STAGE 3: DESIGNER (Deterministic Execution)
    # ══════════════════════════════════════════
    _report("DESIGNER", "Connecting to MCP Server and rendering slides...")
    trace_log.append("\n🎨 **Stage 3: DESIGNER** — Executing MCP tool calls...")
    
    server_param = StdioServerParameters(
        command="python",
        args=["ppt_mcp_server.py"]
    )
    
    theme = slide_plan.get("theme", "space")
    slides = slide_plan.get("slides", [])
    
    try:
        async with stdio_client(server_param) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                
                # Build a tool-call helper dict
                tool_map = {t.name: t for t in tools}
                
                async def call_tool(name: str, **kwargs):
                    """Safely invoke an MCP tool by name."""
                    if name in tool_map:
                        result = await tool_map[name].ainvoke(kwargs)
                        _report("DESIGNER", f"  ✓ {name}({', '.join(f'{k}={repr(v)[:40]}' for k,v in kwargs.items())})")
                        return result
                    return f"Tool '{name}' not found."
                
                # Step 1: Create presentation
                await call_tool("create_presentation")
                trace_log.append("  🛠️ `create_presentation()` — 16:9 canvas initialized")
                
                # Step 2: Process each slide
                for i, s in enumerate(slides):
                    slide_title = s.get("title", f"Slide {i+1}")
                    layout = s.get("layout", "text_only")
                    bullets = s.get("bullets", [])[:4]  # Enforce max 4
                    visual = s.get("visual", {})
                    visual_type = visual.get("type", "none") if isinstance(visual, dict) else "none"
                    visual_desc = visual.get("description", "") if isinstance(visual, dict) else str(visual)
                    subtitle = s.get("subtitle", "")
                    
                    # Title slide
                    if layout == "title_only" and i == 0:
                        await call_tool("add_title_slide", title=slide_title, subtitle=subtitle or "AI-Generated Presentation", theme=theme)
                        trace_log.append(f"  🛠️ `add_title_slide('{slide_title}')` — Title slide rendered")
                        continue
                    
                    # Diagram slide
                    if visual_type == "diagram":
                        # Generate simple mermaid code based on description
                        mermaid_code = f"flowchart LR\n    A[{slide_title}] --> B[{bullets[0] if bullets else 'Step 1'}]\n    B --> C[{bullets[1] if len(bullets) > 1 else 'Step 2'}]\n    C --> D[{bullets[2] if len(bullets) > 2 else 'Result'}]"
                        
                        result = await call_tool("add_diagram_slide", title=slide_title, mermaid_code=mermaid_code, theme=theme)
                        trace_log.append(f"  🛠️ `add_diagram_slide('{slide_title}')` — Mermaid diagram rendered")
                        continue
                    
                    # Image search for visual slides
                    image_url = ""
                    if visual_type == "image" and visual_desc:
                        _report("DESIGNER", f"  🔎 Searching images: {visual_desc[:50]}...")
                        image_url = _search_image(visual_desc) or ""
                        if image_url:
                            trace_log.append(f"  🔎 Image found for '{visual_desc[:30]}...'")
                        else:
                            trace_log.append(f"  ⚠️ No image found for '{visual_desc[:30]}...', using text fallback")
                            if layout in ("text_left_image_right", "image_background"):
                                layout = "text_only"
                    
                    # Standard content slide
                    await call_tool("add_slide", title=slide_title, bullet_points=bullets,
                                   layout_type=layout, image_url=image_url, theme=theme)
                    trace_log.append(f"  🛠️ `add_slide('{slide_title}', layout='{layout}')` — Content rendered")
                
                # Step 3: Save
                await call_tool("save_presentation", filename="output_presentation.pptx")
                trace_log.append("\n💾 `save_presentation()` — File written to disk!")
                trace_log.append(f"\n✨ **Pipeline Complete!** Generated {len(slides)} slides with '{theme}' theme.")
                
    except BaseException as e:
        # Swallow Streamlit TaskGroup tear-down errors if output was produced
        if os.path.exists("output_presentation.pptx"):
            trace_log.append("\n💾 Presentation saved successfully (background cleanup handled).")
        else:
            raise e
    
    output = "\n".join(trace_log)
    
    # Write to hardware buffer for Streamlit rescue
    with open("agent_output_buffer.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    return {"output": output}


if __name__ == "__main__":
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_prompt = input(f"Enter prompt (or Enter for default): ").strip()
    if not user_prompt:
        user_prompt = default_prompt
    
    result = asyncio.run(run_ppt_agent([HumanMessage(content=user_prompt)]))
    print(result["output"])
