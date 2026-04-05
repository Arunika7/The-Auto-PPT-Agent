# ✨ Auto-PPT Studio: Dual-MCP Agentic Pipeline

An autonomous AI presentation architect built using the **Model Context Protocol (MCP)**, **Streamlit**, and **Qwen/Qwen2.5-7B-Instruct**. This system uses a research-first pipeline to generate professional, "Canva-level" PowerPoint presentations from a single prompt.

---

## 🏛️ Project Architecture: Dual-MCP Orchestration

This project is built as a **Distributed Multi-Agent System** using two independent MCP Servers to decouple research from design.

- **`research_mcp_server.py`**: The "Researcher" node. 
  - `research_topic`: Scours the web for factual truth.
  - `find_image_url`: Locates high-quality visuals (DDG/Pixabay/Picsum).
- **`ppt_mcp_server.py`**: The "Designer" node.
  - `create_presentation`: 16:9 widescreen canvas.
  - `add_title_slide`: Cinematic title/subtitle engine.
  - `add_slide`: 4 layout engines (text+image) with dynamic themes.
  - `add_diagram_slide`: Fixed-position Mermaid flowchart rendering.
- **`agent_ppt.py`**: The "Agentic Brain". Orchestrates both servers in a 4-stage pipeline.
- **`app.py`**: Premium dark-mode UI with a real-time pipeline execution trace.

---

## 🚀 The 4-Stage Pipeline

To ensure "Excellent" grade quality, the agent follows a deterministic 4-stage process:

1.  **RESEARCH (Research MCP):** The agent asks the Research Server to find 16 key facts and relevant image URLs.
2.  **CONTENT (LLM):** The AI synthesizes that research into tight, factual bullet points.
3.  **PLANNER (Agent Logic):** The system drafts a 6-slide structure (Title, Intro, Details, Diagram, Summary, Conclusion).
4.  **DESIGNER (Designer MCP):** The AI invokes the PPT server to render the final `.pptx` file.

---

## ✨ Key Features & Visual Intelligence

- **Agentic Planning:** A full outline is drafted before a single slide tool is called.
- **Automatic Diagrams:** Automatically identifies process flows and generates **Mermaid.js** flowcharts.
- **Dynamic Themes:** 6 vibrant hex-based palettes (Space, Tech, Medical, etc.) applied based on topic keywords.
- **Widescreen Design:** Full 13.3" x 7.5" (16:9) cinematic layouts.
- **Resilient Visuals:** Custom image discovery with **3 fallback layers** so no slide is ever empty.

---

## 🚧 Challenges Faced & Solutions

### 1. Hallucination vs. Reality
**Challenge:** Initially, the AI would invent "facts" about niche topics.
**Solution:** I implemented a **Research MCP** that forces a DuckDuckGo search before writing. If search fails, the agent "hallucinates gracefully" by using its internal knowledge to generate plausible educational content.

### 2. Broken Image Paths
**Challenge:** Web search image links would occasionally be broken or forbidden.
**Solution:** I built a **resilient image engine**. If the primary search fails, the system uses a **Hashed-Seed Picsum** fallback, ensuring every slide always has a relevant, high-quality visual.

### 3. Streamlit Threading Issues
**Challenge:** Streamlit sometimes crashes when running background AI TaskGroups.
**Solution:** I added a **"Hardware Rescue Buffer"**. The agent writes its execution trace to `agent_output_buffer.txt` so the UI can safely recover and display the final result even if the main thread glitches.

---

## 🛠️ Testing with MCP Inspector

Every tool in this project was verified using the **MCP Inspector** before being connected to the AI.
- Run: `npx @modelcontextprotocol/inspector python ppt_mcp_server.py`
- This allows manual verification of layout logic, hex-color application, and image embedding without using any LLM tokens.

---

## 🛠️ Installation & Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment Setup:**
   Create a `.env` file and add your `HUGGINGFACEHUB_API_TOKEN`.
3. **Run the Application:**
   ```bash
   streamlit run app.py
   ```

---

## 📑 Conclusion
By adopting the **Dual-MCP architecture**, this project moves beyond simple scripting into a professional, distributed AI system. The separation of **Research** and **Design** ensures the agent focuses on *what to say*, while the MCP servers focus on *how it looks*.
