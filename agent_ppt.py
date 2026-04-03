from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

import asyncio
import os

async def run_ppt_agent(user_request: str):
    print("Initializing LLM...")
    # Initialize the LLM using native HuggingFace tooling
    llm_endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-Coder-32B-Instruct",
        max_new_tokens=2048,
        temperature=0.1
    )
    llm = ChatHuggingFace(llm=llm_endpoint)

    # 1. Connect to MCP Servers
    print("Connecting to FastMCP Server...")
    server_param = StdioServerParameters(
        command="python",
        args=["ppt_mcp_server.py"]
    )
    
    async with stdio_client(server_param) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 2. Define Agent's Tools from the server
            tools = await load_mcp_tools(session)
            print(f"Loaded tools: {[t.name for t in tools]}")
            
            # 3. Agent Prompt (Crucial for planning)
            system_prompt = '''You are a Presentation Design Agent. Use the available tools to satisfy the user's request.

IMPORTANT: You MUST explicitly plan your actions before executing any tools.
Step 1: Write out a plan with the expected slide titles and structure.
Step 2: First, call 'create_presentation' to initialize the file.
Step 3: For each slide title in your plan, generate an appropriate title and 3-5 bullet points, then call 'add_slide'. 
        If you lack external search tools, gracefully hallucinate plausible and educational content.
Step 4: After all slides are added, call 'save_presentation' passing the file name. Wait! For the filename use the format: output_presentation.pptx
Step 5: Never skip the planning step!'''
            
            # 4. Create and run agent
            print("Creating agent executor...")
            agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
            
            print(f"\\n--- Running Agent for request: '{user_request}' ---\\n")
            result = await agent.ainvoke({"messages": [HumanMessage(content=user_request)]})
            output = result["messages"][-1].content
            print(f"\\n--- Process Complete ---\\nFinal Answer: {output}")
            
            return {"output": output}

if __name__ == "__main__":
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_prompt = input(f"Enter prompt for presentation (or press Enter to use default: '{default_prompt}'): ")
    if not user_prompt.strip():
        user_prompt = default_prompt
        
    asyncio.run(run_ppt_agent(user_prompt))
