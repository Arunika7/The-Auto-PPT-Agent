import streamlit as st
import asyncio
from agent_ppt import run_ppt_agent
from langchain_core.messages import HumanMessage, AIMessage
import os

st.set_page_config(page_title="Auto-PPT Studio", page_icon="✨", layout="wide")

# Premium dark mode CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #0a0a0f;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #c084fc 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 1.1rem;
        font-weight: 400;
        color: #94a3b8;
        margin-bottom: 25px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 24px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #6d28d9 0%, #4f46e5 100%);
        transform: translateY(-1px);
    }
    .status-panel {
        background: linear-gradient(180deg, #1e1b4b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #312e81;
    }
    .trace-box {
        background-color: #0f172a;
        color: #a7f3d0;
        padding: 18px;
        border-radius: 10px;
        margin-top: 10px;
        font-size: 0.9rem;
        border: 1px solid #1e293b;
        line-height: 1.7;
    }
    .pipeline-stage {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 2px 4px;
    }
    .stage-active {
        background-color: #7c3aed;
        color: white;
    }
    .stage-done {
        background-color: #065f46;
        color: #a7f3d0;
    }
    .stage-pending {
        background-color: #1e293b;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">✨ Auto-PPT Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent AI Presentation Architect  •  Planner → Critic → Designer Pipeline</div>', unsafe_allow_html=True)

if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = []

col1, col2 = st.columns([2.5, 1], gap="large")

with col1:
    default_prompt = "Create a 5-slide presentation on the life cycle of a star for a 6th-grade class"
    user_input = st.text_area("📝 Presentation Prompt", value=default_prompt, height=100)
    
    if st.button("🚀 Generate Presentation"):
        if user_input:
            st.session_state.chat_memory.append({"role": "user", "content": user_input})
            
            # Pipeline stage indicators
            stage_container = st.container()
            with stage_container:
                st.markdown("""
                <div style="margin: 10px 0 15px 0;">
                    <span class="pipeline-stage stage-active">🎯 Planner</span>
                    <span style="color:#475569;">→</span>
                    <span class="pipeline-stage stage-pending">🔍 Critic</span>
                    <span style="color:#475569;">→</span>
                    <span class="pipeline-stage stage-pending">🎨 Designer</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Run the multi-agent pipeline with a spinner to indicate progress
            with st.spinner("Executing multi-agent pipeline..."):
                # Convert chat history to LangChain message format
                lc_msgs = []
                for m in st.session_state.chat_memory:
                    if m["role"] == "user":
                        lc_msgs.append(HumanMessage(content=m["content"]))
                    else:
                        lc_msgs.append(AIMessage(content=m["content"]))
                
                try:
                    # Clean up any existing output buffer file
                    if os.path.exists("agent_output_buffer.txt"):
                        os.remove("agent_output_buffer.txt")
                    # Run the PPT agent asynchronously
                    result = asyncio.run(run_ppt_agent(lc_msgs))
                    agent_output = result["output"]
                except BaseException as e:
                    # Handle specific TaskGroup errors or other pipeline failures
                    if "TaskGroup" in str(e) or "TaskGroup" in repr(e):
                        # Fallback: check if the buffer file exists to retrieve output
                        if os.path.exists("agent_output_buffer.txt"):
                            with open("agent_output_buffer.txt", "r", encoding="utf-8") as f:
                                agent_output = f.read()
                        # Fallback: check if the presentation was at least generated
                        elif os.path.exists("output_presentation.pptx"):
                            agent_output = "✨ Presentation generated successfully! Download below."
                        else:
                            st.error(f"Pipeline failed: {str(e)[:200]}")
                            st.stop()
                    else:
                        st.error(f"An error occurred: {e}")
                        st.stop()
            
            # Update pipeline stages to complete
            with stage_container:
                st.markdown("""
                <div style="margin: 10px 0 15px 0;">
                    <span class="pipeline-stage stage-done">✅ Planner</span>
                    <span style="color:#475569;">→</span>
                    <span class="pipeline-stage stage-done">✅ Critic</span>
                    <span style="color:#475569;">→</span>
                    <span class="pipeline-stage stage-done">✅ Designer</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.session_state.chat_memory.append({"role": "assistant", "content": agent_output})
            st.success("✅ Multi-Agent Pipeline Complete!")
            
            st.markdown('#### 📋 Pipeline Execution Trace')
            st.markdown(f'<div class="trace-box">{agent_output}</div>', unsafe_allow_html=True)
        else:
            st.warning("Please enter a prompt first.")

with col2:
    st.markdown("""
    <div class="status-panel">
        <h4 style="margin-top:0px; margin-bottom:15px; color:#c084fc;">⚙️ System Architecture</h4>
        <p style="margin:8px 0; font-size:0.9rem;">🧠 <b>LLM:</b> Qwen2.5-7B-Instruct</p>
        <p style="margin:8px 0; font-size:0.9rem;">🔌 <b>Protocol:</b> MCP stdio</p>
        <p style="margin:8px 0; font-size:0.9rem;">🎨 <b>Engine:</b> python-pptx</p>
        <p style="margin:8px 0; font-size:0.9rem;">🔎 <b>Search:</b> DuckDuckGo</p>
        <p style="margin:8px 0; font-size:0.9rem;">📊 <b>Diagrams:</b> Mermaid.ink</p>
        <hr style="border-color:#312e81; margin:12px 0;">
        <p style="margin:8px 0; font-size:0.85rem; color:#94a3b8;">
            <b>Pipeline:</b> Planner → Critic → Designer<br>
            <b>Themes:</b> 6 palettes<br>
            <b>Layouts:</b> 4 types
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Download button for the generated .pptx file
    base_path = "output_presentation.pptx"
    file_exists = os.path.exists(base_path)
    # Read file data if it exists for the download button
    file_data = open(base_path, "rb").read() if file_exists else b""
    
    st.download_button(
        label="📥 Download .pptx" if file_exists else "⏳ Waiting for Generation...",
        data=file_data,
        file_name="output_presentation.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
        disabled=not file_exists
    )
