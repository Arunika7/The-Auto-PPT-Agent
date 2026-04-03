"""
Auto-PPT Agent: Orchestration Script
------------------------------------
This script acts as the "brain" (Client) of the architecture. It connects to the Hugging Face Serverless Inference API
to power the LLM's reasoning loop. It then establishes an MCP (Model Context Protocol) connection over standard input/output (stdio)
to the local ppt_mcp_server.py application, loads its available actions (tools), and wraps everything into a LangGraph ReAct loop.
"""

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# Load sensitive environment variables from a local .env file
# (e.g., HUGGINGFACEHUB_API_TOKEN) to ensure tokens are securely kept out of version control.
load_dotenv()

import asyncio
import os

async def run_ppt_agent(chat_history: list):
    """
    Main orchestration function that mounts the LangChain application and connects it with the MCP Slide Server.
    
    Why this approach?: The async approach is essential because MCP's 'stdio_client' is fundamentally an asynchronous stream.
    By using an async lifecycle natively, we prevent blocking the main IO thread and ensure seamless bidirectional tool execution.
    """
    print("Initializing LLM...")
    # Initialize the LLM using native HuggingFace tooling
    llm_endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-Coder-32B-Instruct",
        max_new_tokens=2048,
        temperature=0.1
    )
    llm = ChatHuggingFace(llm=llm_endpoint)

    # --- Step 1: Connect to Local MCP Server ---
    print("Connecting to FastMCP Server...")
    
    # We use StdioServerParameters because running the server as a local subprocess pipe via stdout/stdin 
    # is the fastest, lowest-latency transport for local python scripts compared to setting up a local REST API (SSE).
    server_param = StdioServerParameters(
        command="python",
        args=["ppt_mcp_server.py"] # Point specifically to our slide-maker server script
    )
    
    # Establish the low-level read/write streams
    async with stdio_client(server_param) as (read, write):
        # Open a high-level ClientSession over those streams
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # --- Step 2: Tool Discovery via Langchain ---
            # load_mcp_tools translates the server's tools into Langchain tools.
            tools = await load_mcp_tools(session)
            
            # Mount Web Search natively
            search_tool = DuckDuckGoSearchRun()
            tools.append(search_tool)
            
            print(f"Loaded tools: {[t.name for t in tools]}")
            
            # --- Step 3: Agent Prompt Logic ---
            system_prompt = '''You are a Presentation Design Chatbot. Use the available tools to satisfy the user's request.

IMPORTANT RULES:
- Before writing any slide bullets, you MUST use duckduckgo_search to look up real facts to avoid hallucination. Do not guess facts.
- YOU MUST INCLUDE AT LEAST TWO PICTURES IN EVERY PRESENTATION! To do this, use duckduckgo_search to search for "direct .jpg image URL for [topic]" (like Wikimedia Commons). Once you find a URL that ends in .jpg or .png, call the 'add_image_slide' tool!
- For NEW presentations: First plan, call 'create_presentation', then 'add_title_slide'. 
- For standard body slides, call 'add_slide'. You MUST provide a 'theme_color_hex' string (like #0f172a or #450a0a) to match the topic's vibe dynamically!
- For EDITING: If you need to modify an existing file, call 'open_presentation' first!
- ALWAYS call 'save_presentation' passing the file name (e.g., output_presentation.pptx) after finishing changes.
- Never skip writing out a plan step-by-step first!
- CRITICAL OUTPUT RULE: Your final text response to the user must ONLY be a warm summary of the presentation topics! DO NOT output or disclose any hex color codes, python logic, or tool names to the user!'''
            
            # 4. Create and run agent
            print("Creating agent executor...")
            agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
            
            print(f"\\n--- Running Agent ---\\n")
            # We pass the full conversational chat history directly into the LangGraph 'messages' state!
            result = await agent.ainvoke({"messages": chat_history})
            output = result["messages"][-1].content
            print(f"\\n--- Process Complete ---\\nFinal Answer: {output}")
            
            return {"output": output}

if __name__ == "__main__":
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_prompt = input(f"Enter prompt for presentation (or press Enter to use default: '{default_prompt}'): ")
    if not user_prompt.strip():
        user_prompt = default_prompt
        
    asyncio.run(run_ppt_agent(user_prompt))
