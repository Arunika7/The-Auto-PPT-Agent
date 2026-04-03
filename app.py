import streamlit as st
import asyncio
import os
from agent_ppt import run_ppt_agent

st.set_page_config(page_title="Auto-PPT Studio", page_icon="📝", layout="wide")

# Custom CSS for premium aesthetic
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #111116, #1a1a24);
        color: #ffffff;
    }
    .stButton>button {
        background: linear-gradient(90deg, #7b2cbf, #9d4edd);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(157, 78, 221, 0.4);
        color: #fff;
    }
    h1 {
        background: -webkit-linear-gradient(45deg, #e0aaff, #c77dff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌟 Auto-PPT Studio")
st.markdown("### Autonomous AI Presentation Architect")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("Provide a presentation topic, and the LangChain + MCP agent will dynamically plan the structure, generate educational content, and execute local disk tools to craft your PowerPoint file.")
    prompt = st.text_area(
        "📝 Presentation Prompt Configuration", 
        value="Create a 5-slide presentation on the life cycle of a star for a 6th-grade class",
        height=150
    )
    generate_btn = st.button("🚀 Synthesize Presentation")

with col2:
    st.markdown("#### ⚙️ System Status")
    st.info("🧠 **Agent:** Qwen-2.5-Coder\n\n🔌 **Protocol:** MCP stdio\n\n🎨 **Engine:** python-pptx")
    # A placeholder dashboard image or visually pleasing layout component
    st.markdown("<div style='padding:1rem; border:1px solid #333; border-radius:8px; text-align:center;'><p style='color:#a0a0a0'>Ready for Execution</p></div>", unsafe_allow_html=True)

if generate_btn:
    st.markdown("---")
    with st.status("🧠 Agent runtime engaged...", expanded=True) as status:
        try:
            st.write("Initializing FastMCP via stdio...")
            st.write("LangGraph ReAct Agent started...")
            
            # We run the async agent
            result = asyncio.run(run_ppt_agent(prompt))
            
            status.update(label="✅ Generation Complete!", state="complete", expanded=False)
            
            st.markdown("### 📋 AI Execution Trace")
            st.success(result.get("output"))
            
            output_file = "output_presentation.pptx"
            if os.path.exists(output_file):
                with open(output_file, "rb") as file:
                    st.download_button(
                        label="⬇️ Download Output File (.pptx)",
                        data=file,
                        file_name="output_presentation.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
            else:
                st.error("Operation finished successfully, but `output_presentation.pptx` could not be found on disk.")
                
        except Exception as e:
            status.update(label="❌ Fatal Error Detected", state="error")
            st.error(f"Exception Trace:\n{type(e).__name__}: {e}")
            st.warning("Hint: Check your terminal for deep tracebacks. This may be caused by an invalid `.env` HuggingFace Token, or a locked MCP stdio process.")
