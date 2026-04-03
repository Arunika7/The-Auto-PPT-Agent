"""
PowerPoint MCP Server (FastMCP Environment)
-------------------------------------------
This script defines the standalone tool server utilizing python-pptx.
It acts as a backend node. When executed by the LangGraph agent, it exposes
3 discrete tools to manipulate an active PowerPoint presentation document.
"""

from mcp.server.fastmcp import FastMCP
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import os
import requests
from io import BytesIO

# Initialize FastMCP Server context. This binds the app routes.
mcp = FastMCP("PowerPoint MCP Server")

# --- Critical Architectural State ---
# Global state variable to store the in-memory PPTX object during the lifecycle of the session.
# Why?: Because MCP commands over standard input/output are isolated tool calls conceptually. 
# We must store the Presentation object here globally so `add_slide` edits the same active instance
# that `create_presentation` instantiated.
_current_prs = None

@mcp.tool()
def create_presentation() -> str:
    """
    Initializes a new blank PowerPoint presentation in memory.
    Must be called before adding any slides.
    Returns a success message.
    """
    global _current_prs
    _current_prs = Presentation()
    # Lock to Modern 16:9 Aspect Ratio
    _current_prs.slide_width = Inches(13.333)
    _current_prs.slide_height = Inches(7.5)
    return "New blank 16:9 presentation has been created in memory. You can now add slides."

@mcp.tool()
def open_presentation(filename: str) -> str:
    """
    Opens an existing PowerPoint file from disk into memory so it can be modified.
    Use this if the user asks to edit the existing file.
    Args:
        filename: The filename (e.g., 'output_presentation.pptx')
    """
    global _current_prs
    if not filename.endswith('.pptx'):
        filename += '.pptx'
    if not os.path.exists(filename):
        return f"Error: No such file '{filename}' exists on disk."
    
    _current_prs = Presentation(filename)
    return f"Successfully opened {filename}. It currently has {len(_current_prs.slides)} slides. You can now modify it."

@mcp.tool()
def add_title_slide(main_title: str, subtitle: str, theme_color_hex: str = "#1E1E2E") -> str:
    """
    Adds a large Title Slide. You should use this for the very first slide of the presentation.
    Args:
        main_title: The big main title.
        subtitle: The smaller sub-text below.
        theme_color_hex: A 6-character hex color string for the slide background.
    """
    global _current_prs
    if _current_prs is None: return "Error: No presentation exists."
    
    slide = _current_prs.slides.add_slide(_current_prs.slide_layouts[0])
    
    # Parse dynamic hex color
    hex_clean = theme_color_hex.lstrip('#')
    if len(hex_clean) != 6: hex_clean = "1E1E2E"
    r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    
    background = slide.background
    background.fill.solid()
    background.fill.fore_color.rgb = RGBColor(r, g, b)
    
    if slide.shapes.title:
        slide.shapes.title.text = main_title
        for p in slide.shapes.title.text_frame.paragraphs:
            p.font.name = "Segoe UI"
            p.font.size = Pt(54)
            p.font.color.rgb = RGBColor(255, 255, 255) # Clean White Header
            p.font.bold = True
            
    if len(slide.placeholders) > 1:
        sub = slide.placeholders[1]
        sub.text = subtitle
        for p in sub.text_frame.paragraphs:
            p.font.name = "Segoe UI"
            p.font.size = Pt(28)
            p.font.color.rgb = RGBColor(200, 200, 200) # Soft grey subtitle
            
    return f"Title slide '{main_title}' added successfully."

@mcp.tool()
def add_slide(title: str, bullet_points: list[str], theme_color_hex: str = "#1E1E2E") -> str:
    """
    Adds a new slide to the current presentation.
    Args:
        title: The title of the slide.
        bullet_points: A list of strings, each representing a bullet point.
        theme_color_hex: A 6-character hex color string for the slide background (e.g. '#FF0000'). Default is dark blue.
    Returns:
        A success message indicating the slide was added.
    """
    global _current_prs
    
    # Protective Exception Handling: Prevents the agent from acting out-of-bounds
    if _current_prs is None:
        return "Error: No presentation exists. Call create_presentation first."

    # Slide array reference. Layout index 1 corresponds inherently to "Title and Content" in standard themes.
    slide_layout = _current_prs.slide_layouts[1] 
    slide = _current_prs.slides.add_slide(slide_layout)
    
    # Parse dynamic hex color
    hex_clean = theme_color_hex.lstrip('#')
    if len(hex_clean) != 6: hex_clean = "1E1E2E"
    r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
    
    # --- Dynamic Background Styling ---
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(r, g, b)
    
    # Set the title and style it
    title_shape = slide.shapes.title
    if title_shape:
        title_shape.text = title
        for p in title_shape.text_frame.paragraphs:
            p.font.name = "Segoe UI"
            p.font.size = Pt(44)
            p.font.color.rgb = RGBColor(224, 170, 255) # Pastel purple gradient feel
            p.font.bold = True
        
    # Set bullet points and style them
    body_shape = slide.placeholders[1]
    tf = body_shape.text_frame
    tf.text = "" # Clear default text if any
    
    for i, bullet in enumerate(bullet_points):
        if i == 0:
            p = tf.paragraphs[0]
            p.text = bullet
        else:
            p = tf.add_paragraph()
            p.text = bullet
            p.level = 0
            
        # Style each bullet
        p.font.name = "Segoe UI"
        p.font.size = Pt(24)
        p.font.color.rgb = RGBColor(220, 220, 230) # Soft bright white
        
    return f"Slide '{title}' added successfully with {len(bullet_points)} stylized bullet points."

@mcp.tool()
def add_image_slide(title: str, image_url: str, description: str) -> str:
    """
    Downloads an image from the internet and adds a new slide specifically displaying that image.
    Args:
        title: Title of the slide.
        image_url: A valid internet URL pointing directly to a .jpg or .png picture.
        description: A short caption or educational text.
    """
    global _current_prs
    if _current_prs is None: return "Error no presentation exists"
    
    # Actively Download Content using HTTP GET locally
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image_stream = BytesIO(response.content)
    except Exception as e:
        return f"Error downloading image from {image_url}: {str(e)}"
        
    # Use Layout 5 ("Title Only") to leave the body entirely empty for absolute custom shape positioning.
    slide = _current_prs.slides.add_slide(_current_prs.slide_layouts[5]) 
    
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(20, 20, 25) # Dark modern slate
    
    if slide.shapes.title:
        slide.shapes.title.text = title
        for p in slide.shapes.title.text_frame.paragraphs:
            p.font.name = "Segoe UI"
            p.font.size = Pt(44)
            p.font.color.rgb = RGBColor(224, 170, 255)
            p.font.bold = True
            
    # Add picture seamlessly using python-pptx positional scaling engine
    try:
        # Centered roughly for 16:9
        slide.shapes.add_picture(image_stream, Inches(3.5), Inches(1.5), height=Inches(4.5))
    except Exception as e:
        return f"Error adding image format to slide: {str(e)}"
        
    # Inject Custom HTML-styled Text Box
    txBox = slide.shapes.add_textbox(Inches(1), Inches(6.2), Inches(11.3), Inches(1))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = description
    p.font.name = "Segoe UI"
    p.font.size = Pt(20)
    p.font.color.rgb = RGBColor(220, 220, 230)
    
    return f"Image slide '{title}' correctly downloaded and attached."

@mcp.tool()
def add_speaker_notes(notes: str) -> str:
    """
    Injects a long paragraph of speaker speech notes into the very last slide that was created.
    Call this immediately after add_slide.
    """
    global _current_prs
    if _current_prs is None or len(_current_prs.slides) == 0:
        return "Error: No active slides exist to attach notes to."
    
    slide = _current_prs.slides[-1] # The latest slide
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = notes
    return "Speaker notes successfully injected into the slide."

@mcp.tool()
def save_presentation(filename: str) -> str:
    """
    Saves the in-memory presentation to the local disk.
    Args:
        filename: The name of the file (will be automatically overridden to sync with UI).
    Returns:
        A success message.
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists to save."
        
    # We explicitly force the filename to the exact string Streamlit expects for the Download button
    filename = "output_presentation.pptx"
        
    # Save the presentation
    _current_prs.save(filename)
    
    # We DO NOT set _current_prs = None here anymore!
    # This allows conversational chatbot memory to continue editing the file if the user adds further chat prompts!
    
    return f"Presentation successfully saved to {filename}"

if __name__ == "__main__":
    mcp.run()
