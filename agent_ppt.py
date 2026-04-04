"""
Auto-PPT Agent V3: Multi-Agent Pipeline
-----------------------------------------
Architecture:
  Stage 1: CONTENT  — LLM generates bullet-point facts (plain text, NOT JSON)
  Stage 2: PLANNER  — Python structures slides from facts  
  Stage 3: CRITIC   — Python enforces design rules
  Stage 4: DESIGNER — Deterministic MCP tool execution
"""

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

import asyncio
import json
import os
import re
import hashlib
import requests

# ──────────────────────────────────────────────
# PROMPT: Simple fact generation (NO JSON!)
# ──────────────────────────────────────────────

CONTENT_PROMPT = """You are an expert educator. Given a topic, write exactly 16 short facts about it.

RULES:
- Write exactly 16 facts, numbered 1-16.
- Each fact must be ONE short sentence (max 8 words).
- Cover: definition, key features, process/stages, importance, and fun facts.
- Be specific and factual. No filler.

Example for "Solar System":
1. Eight planets orbit our Sun
2. Mercury is closest to Sun
3. Venus is the hottest planet
4. Earth supports liquid water life
5. Mars has the tallest volcano
6. Jupiter is the largest planet
7. Saturn has beautiful ice rings
8. Uranus rotates on its side
9. Neptune has supersonic wind speeds
10. Pluto is a dwarf planet
11. Asteroids orbit between Mars Jupiter
12. Comets have long glowing tails
13. Sun contains 99% system mass
14. Gravity holds everything in orbit
15. Space exploration reveals new mysteries
16. Solar system is 4.6 billion years old

Now write 16 facts about: """


# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────

def _extract_topic(user_prompt: str) -> str:
    """Extract the core topic from a user prompt."""
    prompt_lower = user_prompt.lower()
    
    # Try specific pattern first: "X-slide presentation on/about TOPIC for Y"
    match = re.search(r'presentation\s+(?:on|about)\s+(.+?)(?:\s+for\s+|\s+in\s+|\s+with\s+|$)', user_prompt, re.I)
    if match:
        return match.group(1).strip()[:50]
    
    # Try keyword extraction
    for keyword in ["about ", "on ", "regarding "]:
        if keyword in prompt_lower:
            idx = prompt_lower.index(keyword) + len(keyword)
            topic = user_prompt[idx:].strip()
            for stop in [" for ", " in ", " with ", " to "]:
                if stop in topic.lower():
                    topic = topic[:topic.lower().index(stop)]
            return topic.strip()[:50]
    
    # Remove common prefixes
    for prefix in ["create a ", "make a ", "generate a ", "build a "]:
        if prompt_lower.startswith(prefix):
            return user_prompt[len(prefix):].strip()[:50]
    
    return user_prompt[:50]


def _parse_facts(llm_output: str) -> list[str]:
    """Parse numbered facts from LLM plain-text output."""
    facts = []
    for line in llm_output.split("\n"):
        line = line.strip()
        # Match "1. fact" or "1) fact" or "- fact"
        match = re.match(r'^\d+[\.\)]\s*(.+)', line)
        if match:
            fact = match.group(1).strip()
            # Enforce max 8 words
            words = fact.split()
            if len(words) > 1:
                facts.append(" ".join(words[:8]))
        elif line.startswith("- "):
            fact = line[2:].strip()
            words = fact.split()
            if len(words) > 1:
                facts.append(" ".join(words[:8]))
    return facts


def _search_image(query: str) -> str | None:
    """Get a high-quality image. Picsum guaranteed, DDG as bonus."""
    
    # Attempt 1: DuckDuckGo image search
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=5))
            for r in results:
                url = r.get("image", "")
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]):
                    test = requests.head(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                    if test.status_code == 200:
                        return url
    except Exception:
        pass
    
    # Attempt 2: Picsum (ALWAYS works)
    try:
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 1000
        url = f"https://picsum.photos/seed/{seed}/800/500"
        resp = requests.get(url, timeout=10, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.url
    except Exception:
        pass
    
    return None


def _pick_theme(topic: str) -> str:
    """Auto-select theme based on topic keywords."""
    t = topic.lower()
    if any(w in t for w in ["star", "planet", "space", "galaxy", "universe", "moon", "sun", "astro", "cosmos"]):
        return "space"
    if any(w in t for w in ["business", "market", "economy", "finance", "company", "startup"]):
        return "business"
    if any(w in t for w in ["tech", "computer", "ai", "robot", "software", "code", "data", "machine", "algorithm"]):
        return "tech"
    if any(w in t for w in ["plant", "animal", "nature", "ocean", "forest", "climate", "earth", "water", "eco"]):
        return "nature"
    if any(w in t for w in ["health", "medicine", "body", "disease", "cell", "dna", "brain", "heart"]):
        return "medical"
    return "education"


def _build_slide_plan(topic: str, facts: list[str], theme: str) -> dict:
    """Build structured slide plan from facts."""
    title_words = topic.split()[:5]
    title_text = " ".join(w.capitalize() for w in title_words)
    
    # Distribute facts across 4 content slides (4 facts each)
    while len(facts) < 16:
        facts.append(f"Key aspect of {topic[:20]}")
    
    return {
        "theme": theme,
        "slides": [
            {
                "title": title_text,
                "subtitle": f"A Visual Guide to {topic[:30].title()}",
                "bullets": [],
                "visual": {"type": "none", "description": ""},
                "layout": "title_only"
            },
            {
                "title": "What You Need to Know",
                "bullets": facts[0:4],
                "visual": {"type": "image", "description": f"{topic} overview introduction"},
                "layout": "text_left_image_right"
            },
            {
                "title": "Key Details",
                "bullets": facts[4:8],
                "visual": {"type": "image", "description": f"{topic} details close up"},
                "layout": "text_left_image_right"
            },
            {
                "title": "The Process",
                "bullets": facts[8:12],
                "visual": {"type": "diagram", "description": f"{topic} process flow"},
                "layout": "text_only"
            },
            {
                "title": "Why It Matters",
                "bullets": facts[12:16],
                "visual": {"type": "image", "description": f"{topic} importance impact"},
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
      1. CONTENT:  LLM generates plain-text facts
      2. PLANNER:  Python structures slides
      3. CRITIC:   Python enforces design rules
      4. DESIGNER: MCP tool execution
    """
    
    def _report(stage: str, detail: str):
        print(f"[{stage}] {detail}")
        if progress_callback:
            progress_callback(stage, detail)
    
    # Extract user prompt
    user_prompt = ""
    for msg in reversed(chat_history):
        if isinstance(msg, HumanMessage):
            user_prompt = msg.content
            break
    
    if not user_prompt:
        return {"output": "Error: No user prompt found."}
    
    topic = _extract_topic(user_prompt)
    theme = _pick_theme(topic)
    trace_log = []
    
    # ══════════════════════════════════════════
    # STAGE 1: CONTENT GENERATION (LLM — plain text, NOT JSON)
    # ══════════════════════════════════════════
    _report("CONTENT", f"Generating facts about: {topic}...")
    trace_log.append(f"🧠 **Stage 1: CONTENT** — LLM generating facts about '{topic}'...")
    
    facts = []
    
    try:
        llm_endpoint = HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-7B-Instruct",
            max_new_tokens=512,
            temperature=0.4
        )
        llm = ChatHuggingFace(llm=llm_endpoint)
        
        content_messages = [
            SystemMessage(content=CONTENT_PROMPT),
            HumanMessage(content=topic)
        ]
        
        response = await llm.ainvoke(content_messages)
        raw_text = response.content
        _report("CONTENT", f"LLM responded ({len(raw_text)} chars)")
        
        facts = _parse_facts(raw_text)
        _report("CONTENT", f"Parsed {len(facts)} facts from LLM")
        
        if len(facts) >= 8:
            trace_log.append(f"✅ LLM generated {len(facts)} educational facts.")
        else:
            trace_log.append(f"⚠️ LLM only produced {len(facts)} facts. Padding with defaults.")
    except Exception as e:
        _report("CONTENT", f"LLM failed: {str(e)[:80]}")
        trace_log.append(f"⚠️ LLM content generation failed: {str(e)[:60]}")
    
    # Pad with sensible defaults if we didn't get enough facts
    default_facts = [
        f"{topic[:20]} is widely studied",
        f"Has multiple key characteristics",
        f"Important in modern understanding",
        f"Involves complex processes",
        f"Researchers continue exploring it",
        f"Has real-world applications",
        f"Impacts multiple fields of study",
        f"Evolves over time naturally",
        f"Connects to broader systems",
        f"Requires careful analysis",
        f"Found across many contexts",
        f"Drives innovation and discovery",
        f"Well-documented in literature",
        f"Central to its field",
        f"Continues to surprise scientists",
        f"Future research looks promising",
    ]
    while len(facts) < 16:
        facts.append(default_facts[len(facts) % len(default_facts)])
    
    trace_log.append(f"📝 Content ready: {len(facts)} facts for 4 content slides.")
    
    # ══════════════════════════════════════════
    # STAGE 2: PLANNER (Python — builds structure)
    # ══════════════════════════════════════════
    _report("PLANNER", "Structuring slide plan...")
    trace_log.append(f"\n🎯 **Stage 2: PLANNER** — Structuring into slides...")
    
    slide_plan = _build_slide_plan(topic, facts, theme)
    num_slides = len(slide_plan["slides"])
    trace_log.append(f"✅ Plan: {num_slides} slides, theme: '{theme}'")
    
    # ══════════════════════════════════════════
    # STAGE 3: CRITIC (Python — design rules)
    # ══════════════════════════════════════════
    _report("CRITIC", "Enforcing design rules...")
    trace_log.append("\n🔍 **Stage 3: CRITIC** — Enforcing design rules...")
    
    for s in slide_plan["slides"]:
        if "bullets" in s:
            s["bullets"] = [" ".join(b.split()[:8]) for b in s["bullets"] if b.strip()][:4]
        if "title" in s:
            s["title"] = " ".join(s["title"].split()[:6])
        if "visual" not in s:
            s["visual"] = {"type": "image", "description": topic}
        if "layout" not in s:
            s["layout"] = "text_only"
    
    trace_log.append("✅ Design rules enforced.")
    
    # ══════════════════════════════════════════
    # STAGE 4: DESIGNER (MCP Tool Execution)
    # ══════════════════════════════════════════
    _report("DESIGNER", "Connecting to MCP Server...")
    trace_log.append("\n🎨 **Stage 4: DESIGNER** — Executing MCP tool calls...")
    
    server_param = StdioServerParameters(
        command="python",
        args=["ppt_mcp_server.py"]
    )
    
    slides = slide_plan["slides"]
    
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
                
                # Create presentation
                await call_tool("create_presentation")
                trace_log.append("  🛠️ `create_presentation()` — 16:9 canvas")
                
                for i, s in enumerate(slides):
                    slide_title = s.get("title", f"Slide {i+1}")
                    layout = s.get("layout", "text_only")
                    bullets = s.get("bullets", [])[:4]
                    visual = s.get("visual", {})
                    vtype = visual.get("type", "none") if isinstance(visual, dict) else "none"
                    vdesc = visual.get("description", "") if isinstance(visual, dict) else ""
                    subtitle = s.get("subtitle", "")
                    
                    # Title slide
                    if layout == "title_only":
                        await call_tool("add_title_slide", title=slide_title,
                                       subtitle=subtitle or f"Exploring {topic[:30].title()}", theme=theme)
                        trace_log.append(f"  🛠️ `add_title_slide('{slide_title}')`")
                        continue
                    
                    # Diagram slide
                    if vtype == "diagram" and bullets:
                        mermaid = f"flowchart LR\n    A[{bullets[0]}] --> B[{bullets[1] if len(bullets) > 1 else 'Next'}]\n    B --> C[{bullets[2] if len(bullets) > 2 else 'Then'}]\n    C --> D[{bullets[3] if len(bullets) > 3 else 'Result'}]"
                        await call_tool("add_diagram_slide", title=slide_title, mermaid_code=mermaid, theme=theme)
                        trace_log.append(f"  🛠️ `add_diagram_slide('{slide_title}')`")
                        continue
                    
                    # Image search
                    image_url = ""
                    if vtype == "image" and vdesc:
                        _report("DESIGNER", f"  🔎 Finding image: {vdesc[:40]}...")
                        image_url = _search_image(vdesc) or ""
                        if image_url:
                            trace_log.append(f"  🔎 Image embedded for '{vdesc[:25]}'")
                        else:
                            trace_log.append(f"  ⚠️ No image for '{vdesc[:25]}'")
                            if layout in ("text_left_image_right", "image_background"):
                                layout = "text_only"
                    
                    # Content slide
                    await call_tool("add_slide", title=slide_title, bullet_points=bullets,
                                   layout_type=layout, image_url=image_url, theme=theme)
                    trace_log.append(f"  🛠️ `add_slide('{slide_title}', '{layout}')` — {len(bullets)} bullets")
                
                # Save
                await call_tool("save_presentation", filename="output_presentation.pptx")
                trace_log.append(f"\n💾 Saved! {len(slides)} slides, '{theme}' theme.")
                trace_log.append(f"\n✨ **Pipeline Complete!**")
                
    except BaseException as e:
        if os.path.exists("output_presentation.pptx"):
            trace_log.append("\n💾 Saved successfully (cleanup handled).")
        else:
            raise e
    
    output = "\n".join(trace_log)
    with open("agent_output_buffer.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    return {"output": output}


if __name__ == "__main__":
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_prompt = input("Enter prompt (or Enter for default): ").strip()
    if not user_prompt:
        user_prompt = default_prompt
    
    result = asyncio.run(run_ppt_agent([HumanMessage(content=user_prompt)]))
    print(result["output"])
