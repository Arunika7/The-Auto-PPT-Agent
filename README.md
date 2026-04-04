# ✨ Auto-PPT Studio: Dual-MCP Agentic Pipeline

An autonomous AI presentation architect built using the **Model Context Protocol (MCP)**, **Streamlit**, and **Qwen/Qwen2.5-7B-Instruct**. This system research-first pipeline generates "Canva-level" PowerPoint presentations from a single prompt.

---

## 🏗️ Architecture: Dual-MCP Orchestration
This project uses **two independent MCP Servers** to decouple research from design.

- **`research_mcp_server.py`**: The "Researcher" node. 
  - `research_topic`: Scours the web for factual truth.
  - `find_image_url`: Locates high-quality visuals (DDG/Pixabay/Picsum).
- **`ppt_mcp_server.py`**: The "Designer" node.
  - `create_presentation`: 16:9 widescreen layout.
  - `add_title_slide`: Cinematic title/subtitle engine.
  - `add_slide`: 4 layout engines (text+image).
  - `add_diagram_slide`: Renders Mermaid flowcharts into slides.
- **`agent_ppt.py`**: The "Agentic Brain". Orchestrates both servers in a 4-stage pipeline.
- **`app.py`**: Premium dark-mode UI with real-time pipeline execution trace.

---

## 🚀 Key Features
- **Agentic Planning:** Explicit outline drafted before any PPT tools are called.
- **Visual Intelligence:** Guaranteed image embedding on every slide.
- **Diagram Support:** Automatic Mermaid flowchart generation for process flows.
- **16:9 Widescreen:** Modern cinematic layouts.
- **Robustness:** Seeded image search and "Hardware Buffer" to handle Streamlit threading issues.

---

## 🛠️ Setup & Run

1. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment Configuration:**
   Add your `HUGGINGFACEHUB_API_TOKEN` to `.env`.
3. **Launch the UI:**
   ```bash
   streamlit run app.py
   ```

---

## 🛠️ MCP Tooling: Multi-Server Access
The Agent connects to both servers over the MCP `stdio` transport. 

**Designer Server Inspector:**
```bash
npx @modelcontextprotocol/inspector python ppt_mcp_server.py
```

**Research Server Inspector:**
```bash
npx @modelcontextprotocol/inspector python research_mcp_server.py
```
