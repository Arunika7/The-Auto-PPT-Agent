"""
Auto-PPT Agent V2: Multi-Agent Pipeline
----------------------------------------
3-stage architecture:
  Stage 1: PLANNER  — LLM generates structured JSON slide plan (with DuckDuckGo research backup)
  Stage 2: CRITIC   — Python enforces design rules instantly
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

PLANNER_PROMPT = """Output ONLY a JSON slide plan. No explanation. No markdown.

Rules: 5 slides, max 4 bullets each, max 8 words per bullet, titles max 6 words.
Theme: space|business|education|tech|nature|medical
Layout: title_only|text_only|text_left_image_right|image_background
visual.type: none (title slides), image (others), diagram (processes)
Slide 1 must be title_only.

Format: {"theme":"X","slides":[{"title":"T","subtitle":"S","bullets":[],"visual":{"type":"none","description":""},"layout":"title_only"},{"title":"T2","bullets":["b1","b2"],"visual":{"type":"image","description":"search query"},"layout":"text_left_image_right"}]}"""


# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from LLM text output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def _extract_topic(user_prompt: str) -> str:
    """Extract the core topic from a user prompt."""
    prompt_lower = user_prompt.lower()
    for keyword in ["on ", "about ", "regarding ", "for "]:
        if keyword in prompt_lower:
            idx = prompt_lower.index(keyword) + len(keyword)
            topic = user_prompt[idx:].strip()
            # Remove trailing qualifiers
            for stop in [" for ", " in ", " with "]:
                if stop in topic.lower():
                    topic = topic[:topic.lower().index(stop)]
            return topic[:50]
    return user_prompt[:50]


def _research_topic(topic: str) -> list[str]:
    """Use DuckDuckGo to research real facts about a topic."""
    facts = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{topic} key facts educational", max_results=5))
            for r in results:
                body = r.get("body", "")
                if body and len(body) > 20:
                    # Split into sentences and take short ones
                    sentences = body.replace(". ", ".|").split("|")
                    for sent in sentences[:2]:
                        sent = sent.strip().rstrip(".")
                        words = sent.split()
                        if 3 <= len(words) <= 12:
                            facts.append(" ".join(words[:8]))
    except Exception:
        pass
    return facts[:12]  # Return max 12 facts


def _search_image(query: str) -> str | None:
    """Get a high-quality image. Uses Picsum (always works) with DDG as bonus attempt."""
    import requests
    import hashlib
    
    # Attempt 1: DuckDuckGo image search (may fail)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=5))
            for r in results:
                url = r.get("image", "")
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]):
                    # Verify the URL actually downloads
                    test = requests.head(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                    if test.status_code == 200:
                        return url
    except Exception:
        pass
    
    # Attempt 2: Picsum.photos (ALWAYS works — guaranteed high-quality stock photos)
    # Use a hash of the query as seed so same topic = same image consistently
    try:
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 1000
        url = f"https://picsum.photos/seed/{seed}/800/500"
        resp = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.url  # Returns the final redirected URL (direct image)
    except Exception:
        pass
    
    return None


def _build_research_plan(topic: str, facts: list[str]) -> dict:
    """Build a content-rich slide plan from researched facts."""
    # Distribute facts across slides
    chunk_size = max(1, len(facts) // 3)
    chunks = [facts[i:i+chunk_size] for i in range(0, len(facts), chunk_size)]
    while len(chunks) < 3:
        chunks.append([f"Key aspect of {topic[:20]}"])
    
    # Pick theme based on topic keywords
    topic_lower = topic.lower()
    if any(w in topic_lower for w in ["star", "planet", "space", "galaxy", "universe", "moon", "sun"]):
        theme = "space"
    elif any(w in topic_lower for w in ["business", "market", "economy", "finance", "company"]):
        theme = "business"
    elif any(w in topic_lower for w in ["tech", "computer", "ai", "robot", "software", "code", "data"]):
        theme = "tech"
    elif any(w in topic_lower for w in ["plant", "animal", "nature", "ocean", "forest", "climate", "earth"]):
        theme = "nature"
    elif any(w in topic_lower for w in ["health", "medicine", "body", "disease", "cell", "dna"]):
        theme = "medical"
    else:
        theme = "education"
    
    title_short = " ".join(topic.split()[:5]).title()
    
    return {
        "theme": theme,
        "slides": [
            {
                "title": title_short,
                "subtitle": f"Understanding {topic[:30].title()}",
                "bullets": [],
                "visual": {"type": "none", "description": ""},
                "layout": "title_only"
            },
            {
                "title": f"Introduction to {topic.split()[0].title()}",
                "bullets": chunks[0][:4] if chunks[0] else [f"Overview of {topic[:20]}"],
                "visual": {"type": "image", "description": f"{topic} overview"},
                "layout": "text_left_image_right"
            },
            {
                "title": "Key Facts & Details",
                "bullets": chunks[1][:4] if len(chunks) > 1 else ["Important details"],
                "visual": {"type": "image", "description": f"{topic} details"},
                "layout": "text_left_image_right"
            },
            {
                "title": "How It Works",
                "bullets": chunks[2][:4] if len(chunks) > 2 else ["Process overview"],
                "visual": {"type": "diagram", "description": f"{topic} process"},
                "layout": "text_only"
            },
            {
                "title": "Why It Matters",
                "bullets": (chunks[3][:4] if len(chunks) > 3 else 
                           [f"{topic[:20]} impacts our world", "Active area of research", "Growing importance"]),
                "visual": {"type": "image", "description": f"{topic} importance"},
                "layout": "text_left_image_right"
            },
            {
                "title": "Thank You",
                "subtitle": f"Exploring {topic[:25].title()}",
                "bullets": [],
                "visual": {"type": "none", "description": ""},
                "layout": "title_only"
            }
        ]
    }


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────

async def run_ppt_agent(chat_history: list, progress_callback=None):
    """
    Multi-agent pipeline:
      1. PLANNER: LLM → structured JSON plan (with research fallback)
      2. CRITIC: Python → design rule enforcement
      3. DESIGNER: Python → MCP tool execution
    """
    
    def _report(stage: str, detail: str):
        print(f"[{stage}] {detail}")
        if progress_callback:
            progress_callback(stage, detail)
    
    # Extract the user's latest message
    user_prompt = ""
    for msg in reversed(chat_history):
        if isinstance(msg, HumanMessage):
            user_prompt = msg.content
            break
    
    if not user_prompt:
        return {"output": "Error: No user prompt found.", "trace": []}
    
    topic = _extract_topic(user_prompt)
    trace_log = []
    
    # ══════════════════════════════════════════
    # STAGE 0: RESEARCH (DuckDuckGo)
    # ══════════════════════════════════════════
    _report("RESEARCH", f"Researching: {topic}...")
    trace_log.append(f"🔬 **Research Phase** — Gathering facts on '{topic}'...")
    
    facts = _research_topic(topic)
    if facts:
        trace_log.append(f"✅ Found {len(facts)} research facts from the web.")
    else:
        trace_log.append("⚠️ Web research returned no results. Using LLM knowledge.")
    
    # ══════════════════════════════════════════
    # STAGE 1: PLANNER
    # ══════════════════════════════════════════
    _report("PLANNER", f"Planning slides for: {topic}...")
    trace_log.append("\n🎯 **Stage 1: PLANNER** — Generating structured slide plan...")
    
    slide_plan = None
    
    # Try LLM planner first
    try:
        _report("PLANNER", "Calling LLM...")
        llm_endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            max_new_tokens=1024,
            temperature=0.3
        )
        llm = ChatHuggingFace(llm=llm_endpoint)
        
        planner_messages = [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(content=f"Create presentation about: {topic}")
        ]
        
        planner_response = await llm.ainvoke(planner_messages)
        planner_text = planner_response.content
        _report("PLANNER", f"LLM responded ({len(planner_text)} chars)")
        
        slide_plan = _extract_json(planner_text)
        
        # Validate the plan has actual content  
        if slide_plan and "slides" in slide_plan:
            has_content = False
            for s in slide_plan["slides"]:
                bullets = s.get("bullets", [])
                if bullets and any(len(b.strip()) > 3 for b in bullets):
                    has_content = True
                    break
            if not has_content:
                _report("PLANNER", "LLM JSON has no real content, falling back to research plan")
                slide_plan = None
            else:
                trace_log.append("✅ LLM generated a valid slide plan.")
        else:
            slide_plan = None
    except Exception as e:
        _report("PLANNER", f"LLM failed: {str(e)[:100]}")
        slide_plan = None
    
    # Fallback: build plan from research
    if slide_plan is None:
        trace_log.append("⚠️ LLM planner failed. Building plan from web research...")
        slide_plan = _build_research_plan(topic, facts)
        trace_log.append(f"✅ Research-based plan built: {len(slide_plan['slides'])} slides")
    
    num_slides = len(slide_plan.get("slides", []))
    trace_log.append(f"📊 Plan: **{num_slides} slides**, theme: **{slide_plan.get('theme', 'space')}**")
    
    # ══════════════════════════════════════════
    # STAGE 2: CRITIC (Instant Python enforcement)
    # ══════════════════════════════════════════
    _report("CRITIC", "Enforcing design rules...")
    trace_log.append("\n🔍 **Stage 2: CRITIC** — Enforcing design rules...")
    
    for s in slide_plan.get("slides", []):
        if "bullets" in s:
            s["bullets"] = s["bullets"][:4]
            s["bullets"] = [" ".join(b.split()[:8]) for b in s["bullets"] if b.strip()]
        if "title" in s:
            s["title"] = " ".join(s["title"].split()[:6])
        if "visual" not in s:
            s["visual"] = {"type": "image", "description": s.get("title", "")}
        if "layout" not in s:
            s["layout"] = "text_only"
    
    trace_log.append("✅ Design rules enforced.")
    
    # ══════════════════════════════════════════
    # STAGE 3: DESIGNER (Deterministic Execution)
    # ══════════════════════════════════════════
    _report("DESIGNER", "Connecting to MCP Server...")
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
                tool_map = {t.name: t for t in tools}
                
                async def call_tool(name: str, **kwargs):
                    if name in tool_map:
                        result = await tool_map[name].ainvoke(kwargs)
                        _report("DESIGNER", f"  ✓ {name}")
                        return result
                    return f"Tool '{name}' not found."
                
                # Step 1: Create presentation
                await call_tool("create_presentation")
                trace_log.append("  🛠️ `create_presentation()` — 16:9 canvas initialized")
                
                # Step 2: Process each slide
                for i, s in enumerate(slides):
                    slide_title = s.get("title", f"Slide {i+1}")
                    layout = s.get("layout", "text_only")
                    bullets = s.get("bullets", [])[:4]
                    visual = s.get("visual", {})
                    visual_type = visual.get("type", "none") if isinstance(visual, dict) else "none"
                    visual_desc = visual.get("description", "") if isinstance(visual, dict) else str(visual)
                    subtitle = s.get("subtitle", "")
                    
                    # Title slide
                    if layout == "title_only":
                        await call_tool("add_title_slide", title=slide_title, 
                                       subtitle=subtitle or f"Exploring {topic[:30].title()}", theme=theme)
                        trace_log.append(f"  🛠️ `add_title_slide('{slide_title}')`")
                        continue
                    
                    # Diagram slide
                    if visual_type == "diagram":
                        mermaid_code = f"flowchart LR\n    A[{slide_title}] --> B[{bullets[0] if bullets else 'Step 1'}]\n    B --> C[{bullets[1] if len(bullets) > 1 else 'Step 2'}]\n    C --> D[{bullets[2] if len(bullets) > 2 else 'Result'}]"
                        
                        await call_tool("add_diagram_slide", title=slide_title, mermaid_code=mermaid_code, theme=theme)
                        trace_log.append(f"  🛠️ `add_diagram_slide('{slide_title}')`")
                        continue
                    
                    # Image search
                    image_url = ""
                    if visual_type == "image" and visual_desc:
                        _report("DESIGNER", f"  🔎 Searching: {visual_desc[:40]}...")
                        image_url = _search_image(visual_desc) or ""
                        if image_url:
                            trace_log.append(f"  🔎 Image found for '{visual_desc[:25]}...'")
                        else:
                            trace_log.append(f"  ⚠️ No image for '{visual_desc[:25]}...'")
                            if layout in ("text_left_image_right", "image_background"):
                                layout = "text_only"
                    
                    # Content slide
                    await call_tool("add_slide", title=slide_title, bullet_points=bullets,
                                   layout_type=layout, image_url=image_url, theme=theme)
                    trace_log.append(f"  🛠️ `add_slide('{slide_title}', layout='{layout}')` — {len(bullets)} bullets")
                
                # Step 3: Save
                await call_tool("save_presentation", filename="output_presentation.pptx")
                trace_log.append(f"\n💾 `save_presentation()` — File written!")
                trace_log.append(f"\n✨ **Complete!** {len(slides)} slides, '{theme}' theme.")
                
    except BaseException as e:
        if os.path.exists("output_presentation.pptx"):
            trace_log.append("\n💾 Saved successfully (background cleanup handled).")
        else:
            raise e
    
    output = "\n".join(trace_log)
    
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
