# Auto-PPT Agent

An autonomous conversational Agent built using Streamlit, LangGraph, and the Model Context Protocol (MCP) that can independently research facts, scrape images, and natively format cinematic PowerPoint presentations.

## Overview

This project elevates typical AI pipelines by natively routing an open-source Hugging Face LLM into a sophisticated **MCP Server** utilizing `python-pptx`, achieving dynamic presentation rendering exclusively through autonomous tool execution.

## Architecture
- **`ppt_mcp_server.py`**: A stateless backend node governed by `FastMCP`. Exposes highly constrained formatting tools forcing 16:9 cinematic output, dynamic RGB color styling algorithms, and direct HTTP binary chunking to scrape internet image URLs into PowerPoint layouts.
- **`agent_ppt.py`**: A `LangGraph` orchestrator looping over `langchain-mcp-adapters` and natively binding the `DuckDuckGoSearchRun` tool suite. Forces the LLM to research the internet for concrete truth before generating any parameters.
- **`app.py`**: The dynamic Python Streamlit graphical user interface allowing memory-enabled multi-turn chat loops to continually modify the output natively.

## Prerequisites

- Python 3.10+
- A Hugging Face API Token (HUGGINGFACEHUB_API_TOKEN)

## Setup

1. Open a terminal and navigate to this folder.
2. Create and activate a Virtual Environment (Optional but recommended).
   ```bash
   python -m venv venv
   # Windows:
   venv\\Scripts\\activate
   # Mac/Linux:
   source venv/bin/activate
   ```
3. Install Requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` and add your Hugging Face API key.
   ```bash
   echo HUGGINGFACEHUB_API_TOKEN="hf_your_token_here" > .env
   ```

## Running the Application
Launch the rich graphical user interface via Streamlit:
```bash
streamlit run app.py
```
This boots up a fully styled interactive dashboard where you can prompt the autonomous agent in natural language.

### Debugging: MCP Inspector
If you wish to test the backend PowerPoint logic without firing up the LLM, you can directly launch Anthropic's visual GUI natively via your terminal:
```bash
npx @modelcontextprotocol/inspector python ppt_mcp_server.py
```
