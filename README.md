# ✨ Auto-PPT Studio - Multi-Agent AI Presentation Architect
Intelligent Streamlit-based agent that orchestrates PowerPoint presentation generation through a 4-phase agentic loop with Model Context Protocol (MCP) server integration.

**Status:** Production Ready | **Version:** 1.0.0 | **Framework:** Streamlit + LangChain + MCP

---

## 🎯 What is the Agent?
The **Auto-PPT Agent** is a distributed AI system that automates professional presentation creation. It:

- **Receives** natural language prompts from the user.
- **Researches** factual content using the Research MCP Server.
- **Synthesizes** research into tight, educational bullet points using LLMs.
- **Plans** a coherent slide structure with logical flow and visual descriptions.
- **Renders** professional .pptx files using the Designer MCP Server with dynamic themes.

---

## 🚀 Quick Start
### Prerequisites
- Python 3.10+
- pip (Python package manager)
- **Hugging Face API Token** (for LLM access)

### Installation Steps
#### Step 1: Clone and Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```
**Key Libraries:**
- `streamlit`: Premium dark-mode UI
- `langchain`: AI orchestration framework
- `mcp`: Model Context Protocol client
- `python-pptx`: PowerPoint manipulation
- `ddgs`: DuckDuckGo research engine

#### Step 3: Configure Environment
Create a `.env` file in the root directory:
```bash
# Edit configuration
HUGGINGFACEHUB_API_TOKEN=your_token_here
```

#### Step 4: Start the Application
```bash
# Launch the Streamlit Studio
streamlit run app.py
```
**Output:**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

---

## 🔄 The 4-Phase Agentic Loop
The agent executes professional presentation generation in 4 distinct phases:

### Phase 1: RESEARCH (2-4 seconds)
- **What Happens:** The agent calls the **Research MCP Server** to scour the web via DuckDuckGo.
- **Input:** Any user-provided topic (e.g., "History of AI", "How stars are born", "A QBR for a retail company")
- **Tool Call:** `research_topic(topic="[extracted_topic]")`
- **Result:** Extraction of 16 key facts and relevant high-fidelity image URLs.

### Phase 2: CONTENT (2-3 seconds)
- **What Happens:** Research data is sent to the LLM (`Qwen2.5-7B-Instruct`).
- **Intelligence:** The LLM synthesizes raw research into concise, action-oriented bullet points (max 8 words per fact).
- **Graceful Fallback:** If research is sparse, the system enters "Hallucination Mode" to generate plausible educational content.

### Phase 3: PLANNER (1 second)
- **What Happens:** The agent drafts a dynamic slide structure tailored to the research content.
- **Typical Structure:**
  - **Title Slide:** Cinematic opening with subtitle.
  - **Contextual Slides:** Introduction and key details with relevant visuals.
  - **Visual Process:** Automatic generation of Mermaid diagrams for workflows.
  - **Impact & Summary:** Closing slides highlighting significance and conclusions.
- **Theme Selection:** Auto-picks from 6 palettes (Space, Tech, Medical, etc.) based on topic keywords.

### Phase 4: DESIGNER (< 2 seconds)
- **What Happens:** The agent calls the **Designer MCP Server** tools to render the final file.
- **Workflow:** `create_presentation()` → `add_title_slide()` → `add_slide()` / `add_diagram_slide()` → `save_presentation()`.
- **Final Result:** A professional `.pptx` file generated on 16:9 widescreen canvas.

---

## 🔗 MCP Servers
The system relies on two specialized MCP servers to decouple research from design.

| Server | Location | Tools | Purpose |
| :--- | :--- | :--- | :--- |
| **Research Server** | `research_mcp_server.py` | `research_topic`, `find_image_url` | Web search and image discovery |
| **Designer Server** | `ppt_mcp_server.py` | `create_presentation`, `add_slide`, `add_diagram_slide`, etc. | Professional PPT Rendering |

---

## 🎨 Design System & Themes
The Designer MCP includes a built-in design system with 6 curated palettes:

- 🌌 **Space:** Dark purple/blue with neon accents.
- 💼 **Business:** Professional deep navy and sky blue.
- 🎓 **Education:** Warm amber and earth tones.
- 💻 **Tech:** Cyberpunk emerald and dark slate.
- 🌿 **Nature:** Modern forest greens.
- 🏥 **Medical:** Soft violet and clinical lavender.

---

## 🛡️ Error Handling & Resilience
- **Research Sparse?** Agent uses internal LLM knowledge to fill gaps.
- **Broken Image Link?** Uses a local **Hashed-Seed Picsum** fallback for guaranteed visuals.
- **Streamlit Glitch?** Uses a **"Hardware Rescue Buffer"** (agent_output_buffer.txt) to capture execution traces safely.
- **Mermaid Failure?** Skips diagram slide and continues with text-only slides to ensure a delivered file.

---

## 🚀 Deployment
### Local Production
1. Set `DEBUG=False` (to be implemented in config.py).
2. Use `streamlit run app.py` on a cloud VM.
3. Ensure port `8501` is open in your firewall.

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

---

## 📚 File Reference
| File | Purpose |
| :--- | :--- |
| `app.py` | Premium Streamlit UI |
| `agent_ppt.py` | Core 4-Phase Orchestration Logic |
| `ppt_mcp_server.py` | MCP PowerPoint Design Server |
| `research_mcp_server.py` | MCP Web Research Server |
| `test_debug.py` | CLI test environment |

---

## 📑 Conclusion
By adopting the **Multi-Agent MCP architecture**, Auto-PPT Studio separates **Content Strategy** from **Visual Design**. This distributed approach ensures the agent can scale across different research and design nodes independently, delivering professional results from a simple text prompt.

Ready to generate amazing presentations! 🚀
