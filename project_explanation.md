# Auto-PPT Agent: Simple Project Overview

## 🌟 What is this project?
The **Auto-PPT Agent** is an AI tool that makes professional PowerPoint presentations for you. You give it one sentence (like *"Explain the life cycle of a star"*), and it does everything else:
1.  It searches the internet for facts.
2.  It finds high-quality images.
3.  It designs the slides with beautiful colors.
4.  It even draws diagrams (like flowcharts) automatically.

---

## 🏗️ How it works (The "Brain")
The project is split into two specialized "workers" called **MCP Servers**. Think of them as experts that the AI can call for help.

### 1. The Researcher (`research_mcp_server.py`)
This worker's job is to find information and images. It looks at the internet and returns real facts so the AI doesn't make mistakes.

### 2. The Designer (`ppt_mcp_server.py`)
This worker is the artist. It knows how to build PowerPoint files, pick colors, and place text and images in the right spots.

---

## 🚀 The 4-Step Process
When you click "Generate," the agent follows these four steps:

### Step 1: Research (Gathering Data)
The agent asks the **Researcher MCP** to find real info about your topic.
```python
# The agent calls a tool to search the web
facts = await research_tool.ainvoke({"topic": "star lifecycle"})
```

### Step 2: Content (Writing the Text)
The AI takes that research and writes 16 short, clear facts. If the internet is slow or information is missing, it "hallucinates gracefully" by using its own smarts to fill in the gaps.

### Step 3: Planning (Organizing Slides)
The AI doesn't just start writing; it makes a **Plan** first. It decides which facts go on which slide and chooses a theme (like "Space" or "Tech").

### Step 4: Designing (Building the PPT)
The agent tells the **Designer MCP** exactly what to build. 
```python
# The agent tells the PPT worker to add a slide
await ppt_tool.ainvoke({
    "title": "Main Stages",
    "bullet_points": ["Nebula", "Main Sequence", "Red Giant"],
    "layout_type": "text_left_image_right",
    "theme": "space"
})
```

---

## ✨ Cool Features Added
- **Mermaid Diagrams:** If your topic is a process (like a lifecycle), the agent automatically draws a flowchart inside the slide.
- **Dynamic Themes:** The colors change based on your topic! Space presentations are dark blue, and medical ones are purple.
- **Widescreen Look:** All slides are in modern 16:9 cinematic format.
- **Smart Pictures:** Every slide has a picture. If it can't find a specific one, it uses a high-quality "fallback" image so the slide never looks empty.

---

## 🛠️ How to use it
1.  Install the needs: `pip install -r requirements.txt`
2.  Add your API Key to the `.env` file.
3.  Run the app: `streamlit run app.py`

This project shows how AI can use separate "expert tools" (MCP) to do complex human tasks perfectly in just a few seconds!
