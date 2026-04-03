import streamlit as st
import asyncio
from agent_ppt import run_ppt_agent
from langchain_core.messages import HumanMessage, AIMessage
import os

st.set_page_config(page_title="Auto-PPT Studio", page_icon="✨", layout="wide")

# CSS mimicking the classic setup exactly as pictured
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #e2e8f0;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #e6b8ff;
        font-family: sans-serif;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #ffffff;
        margin-bottom: 25px;
    }
    .stButton>button {
        background-color: #9d4edd;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 5px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #7b2cbf;
    }
    .status-panel {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    .trace-box {
        background-color: #064e3b; 
        color: #a7f3d0;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">✨ Auto-PPT Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous AI Presentation Architect</div>', unsafe_allow_html=True)
st.write("Provide a presentation topic, and the LangChain + MCP agent will dynamically plan the structure, generate educational content, and execute local disk tools to craft your PowerPoint file.")

st.write("")

if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = []

col1, col2 = st.columns([2.5, 1], gap="large")

with col1:
    # Provide the default prompt about stars as requested
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_input = st.text_area("📄 Presentation Prompt Configuration", value=default_prompt, height=100)
    
    if st.button("🚀 Synthesize Presentation"):
        if user_input:
            st.session_state.chat_memory.append({"role": "user", "content": user_input})
            
            with st.spinner("Executing Toolchain..."):
                lc_msgs = []
                for m in st.session_state.chat_memory:
                    if m["role"] == "user": 
                        lc_msgs.append(HumanMessage(content=m["content"]))
                    else: 
                        lc_msgs.append(AIMessage(content=m["content"]))
                
                try:
                    result = asyncio.run(run_ppt_agent(lc_msgs))
                    agent_output = result["output"]
                    st.session_state.chat_memory.append({"role": "assistant", "content": agent_output})
                    
                    st.success("✔️ Generation Complete!")
                    st.write("Initializing FastMCP via stdio...  \nLangGraph ReAct Agent started...")
                    
                    st.markdown('#### 📄 AI Execution Trace')
                    st.markdown(f'<div class="trace-box">{agent_output}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a prompt first.")

with col2:
    st.markdown("""
    <div class="status-panel">
        <h4 style="margin-top:0px; margin-bottom:15px; color:white;">⚙️ System Status</h4>
        <p style="margin:5px 0;">🧠 Agent: Qwen-2.5-Coder</p>
        <p style="margin:5px 0;">🔌 Protocol: MCP stdio</p>
        <p style="margin:5px 0;">🎨 Engine: python-pptx</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; padding: 12px; border: 1px solid #334155; border-radius: 5px; color: #94a3b8; font-size:0.9rem;">Ready for Execution</div>', unsafe_allow_html=True)
    
    # Download button injection (Always visible, disabled if no file)
    base_path = "output_presentation.pptx"
    file_exists = os.path.exists(base_path)
    file_data = open(base_path, "rb").read() if file_exists else b""
    
    st.download_button(
        label="📥 Download .pptx" if file_exists else "⏳ Waiting for Generation...",
        data=file_data,
        file_name="output_presentation.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
        disabled=not file_exists
    )
