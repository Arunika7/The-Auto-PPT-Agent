# Auto-PPT Agent

An AI Agent built using LangChain and the Model Context Protocol (MCP) that can autonomously create PowerPoint presentations based on a single-sentence prompt.

## Overview

This project satisfies the requirements for the "AI Agents & MCP Architecture" assignment.
The agent connects to a custom `python-pptx` FastMCP Server to access presentation-building tools. The LLM handles the logic and planning of what to write, and uses the MCP Server strictly to perform physical disk operations (file generation, slide generation, text manipulation).

## Architecture
- `ppt_mcp_server.py`: A `FastMCP` server utilizing the `python-pptx` library to create PPT files, add slides, and populate bullet points.
- `agent_ppt.py`: A `langchain` application utilizing `langchain-mcp-adapters` to dynamically load the presentation tools. It uses a `create_react_agent` executor loop, ensuring there is a strict planning step before any tools are invoked.

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

## Running the Agent
Run the main script:
```bash
python agent_ppt.py
```

The script will prompt you for an instructional prompt, or it will use a default ("Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"). 

## Expected Behavior
You will see the agent planning its actions, deciding how many slides to build, and calling the `add_slide` MCP tool multiple times until the presentation is complete. Finally, it will call `save_presentation`, writing `output_presentation.pptx` into the same directory.
