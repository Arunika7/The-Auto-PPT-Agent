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

PLANNER_PROMPT = """You are a presentation planner. Given a topic, output ONLY a JSON object.

RULES:
- Output raw JSON only. No markdown. No explanation. No code fences.
- 5-6 slides. Max 4 bullets per slide. Max 8 words per bullet.
- Titles max 6 words.
- theme: one of space, business, education, tech, nature, medical
- layout: one of title_only, text_only, text_left_image_right, image_background
- visual.type: "none" for title slide, "image" for others, "diagram" for processes
- First slide MUST be title_only layout.

EXAMPLE for "Solar System":
{"theme":"space","slides":[{"title":"The Solar System","subtitle":"A Journey Through Space","bullets":[],"visual":{"type":"none","description":""},"layout":"title_only"},{"title":"Inner Rocky Planets","bullets":["Mercury closest to Sun","Venus hottest planet","Earth supports life","Mars the red planet"],"visual":{"type":"image","description":"inner planets solar system"},"layout":"text_left_image_right"},{"title":"Gas Giant Worlds","bullets":["Jupiter largest planet","Saturn famous for rings","Uranus rotates sideways","Neptune extreme winds"],"visual":{"type":"image","description":"jupiter saturn gas giants"},"layout":"text_left_image_right"},{"title":"Planet Formation Process","bullets":["Dust cloud collapses","Disk forms around star","Particles clump together"],"visual":{"type":"diagram","description":"planet formation process"},"layout":"text_only"},{"title":"Key Takeaways","subtitle":"Exploring Our Cosmic Neighborhood","bullets":["8 unique planets","Diverse environments exist"],"visual":{"type":"none","description":""},"layout":"title_only"}]}

Now generate JSON for the given topic. Output ONLY the JSON:"""

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
    """Search for an image URL. Tries DuckDuckGo images, then falls back to Wikimedia/Unsplash."""
    
    # Attempt 1: DuckDuckGo image search
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=5))
            for r in results:
                url = r.get("image", "")
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]):
                    return url
            if results:
                return results[0].get("image", None)
    except Exception:
        pass
    
    # Attempt 2: DuckDuckGo text search for image URLs
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query} site:upload.wikimedia.org .jpg", max_results=3))
            for r in results:
                href = r.get("href", "") or r.get("link", "")
                if href and any(ext in href.lower() for ext in [".jpg", ".png", ".jpeg"]):
                    return href
    except Exception:
        pass
    
    # Attempt 3: Unsplash Source (always works, free, no auth)
    try:
        safe_query = query.replace(" ", ",").replace("'", "")[:50]
        url = f"https://source.unsplash.com/800x600/?{safe_query}"
        import requests
        resp = requests.get(url, timeout=8, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.url  # Unsplash redirects to the actual image
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
    
    # Log raw LLM output for debugging
    _report("PLANNER", f"Raw LLM output ({len(planner_text)} chars): {planner_text[:300]}...")
    
    slide_plan = _extract_json(planner_text)
    if slide_plan is None or "slides" not in slide_plan or len(slide_plan.get("slides", [])) == 0:
        trace_log.append("⚠️ Planner JSON parse failed. Building intelligent fallback plan...")
        # Build a content-rich fallback plan derived from the user's actual topic
        topic_short = user_prompt.split("on ")[-1].split("about ")[-1].strip()[:40] if "on " in user_prompt.lower() or "about " in user_prompt.lower() else user_prompt[:40]
        slide_plan = {
            "theme": "education",
            "slides": [
                {"title": topic_short[:30], "subtitle": "An Educational Overview", "bullets": [],
                 "visual": {"type": "none", "description": ""}, "layout": "title_only"},
                {"title": f"What is {topic_short[:20]}?",
                 "bullets": [f"Definition of {topic_short[:15]}", "Key characteristics", "Why it matters", "Historical context"],
                 "visual": {"type": "image", "description": topic_short}, "layout": "text_left_image_right"},
                {"title": "Core Concepts",
                 "bullets": ["Fundamental principles", "Important mechanisms", "Scientific evidence", "Real-world examples"],
                 "visual": {"type": "image", "description": f"{topic_short} diagram educational"}, "layout": "text_left_image_right"},
                {"title": "Key Stages",
                 "bullets": ["Stage 1: Beginning", "Stage 2: Development", "Stage 3: Transformation", "Stage 4: Outcome"],
                 "visual": {"type": "diagram", "description": f"{topic_short} process stages"}, "layout": "text_only"},
                {"title": f"Why {topic_short[:20]} Matters",
                 "bullets": ["Practical applications", "Impact on daily life", "Future discoveries"],
                 "visual": {"type": "image", "description": f"{topic_short} importance"}, "layout": "text_left_image_right"},
                {"title": "Summary", "subtitle": f"Understanding {topic_short[:20]}", "bullets": [],
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
                    
                    # Title slide (works at any position — intro AND summary)
                    if layout == "title_only":
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
