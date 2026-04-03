import traceback, asyncio, sys
from agent_ppt import run_ppt_agent
from langchain_core.messages import HumanMessage

async def main():
    try:
        await run_ppt_agent([HumanMessage(content='Create a 2 slide presentation on AI')])
    except Exception as e:
        with open('error_full.txt', 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)

if __name__ == "__main__":
    asyncio.run(main())
