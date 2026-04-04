# Auto-PPT Agent: Reflection & Architecture

## 🚀 Where did your agent fail its first attempt?
In the initial prototyping phase, the agent operated as a single, large **ReAct loop** that tried to research, plan, and render each slide in one go. This failed for two reasons:
1.  **Search Noise:** The agent would fetch real-time web results for "Slide 2" and "Slide 3" separately, but the results were often disjointed, leading to a presentation that didn't tell a coherent story.
2.  **Unreliable Visuals:** Internet image search results would occasionally return "404 Not Found" or "Forbidden" errors, causing the entire agent loop to crash or produce text-only slides.

**The Solution:** I refactored the agent into a **4-stage pipeline** (Research -> Content -> Planner -> Designer). Now, the agent gathers *all* research first and drafts an explicit plan before a single PowerPoint tool is called. I also implemented a **guaranteed visual engine** (DuckDuckGo + Seeded Picsum fallback) so the agent "hallucinates visuals" gracefully if the internet is unreachable.

## 🏗️ How did MCP prevent you from writing hardcoded scripts?
Without the **Model Context Protocol (MCP)**, building a PowerPoint generator typically requires hardcoding the `python-pptx` logic directly into the agent's Python scripts. This creates a "monolithic mess" where design rules (like 16:9 aspect ratios or theme colors) are mixed with AI orchestration.

**With MCP, I achieved perfect decoupling:**
1.  **Server Decoupling:** My `ppt_mcp_server.py` is a standalone "Design Node." I can update the business theme colors or add a new layout engine *without touching a single line of code in the agent*.
2.  **Tool Discovery:** When the agent starts, it doesn't have "hardcoded tools." It dynamically discovers the capabilities of both its **Research Server** and its **Designer Server** via `load_mcp_tools()`. 
3.  **Cross-Platform Ready:** Because I used the MCP `stdio` transport, I could theoretically move the Designer Server to a different machine (e.g., a Windows box with full Office installed) and the Agent Brain could still connect to it without changing its logic.

---

### Conclusion
By adopting the Dual-MCP architecture, I moved from a "hacky script" to a professional **Multi-Agent System**. The separation of Research and Design ensures that the agent focuses on *what* to say, while the MCP server focuses on *how* to look.
