from mcp.server.fastmcp import FastMCP
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import os

# Initialize FastMCP Server
mcp = FastMCP("PowerPoint MCP Server")

# Global state to keep track of the presentation being edited in memory
# (Since MCP servers are stateless in terms of HTTP, stdio persistent process keeps state)
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
    return "New blank presentation has been created in memory. You can now add slides."

@mcp.tool()
def add_slide(title: str, bullet_points: list[str]) -> str:
    """
    Adds a new slide to the current presentation.
    Args:
        title: The title of the slide.
        bullet_points: A list of strings, each representing a bullet point.
    Returns:
        A success message indicating the slide was added.
    """
    global _current_prs
    
    if _current_prs is None:
        return "Error: No presentation exists. Call create_presentation first."

    # Use the bullet slide layout (layout index 1 usually is title and content)
    slide_layout = _current_prs.slide_layouts[1] 
    slide = _current_prs.slides.add_slide(slide_layout)
    
    # Premium Dark Mode Background Styling
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(30, 30, 46) # Deep modern dark grey/blue
    
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
def save_presentation(filename: str) -> str:
    """
    Saves the in-memory presentation to the local disk.
    Args:
        filename: The name of the file (should end in .pptx).
    Returns:
        A success message.
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists to save."
        
    if not filename.endswith('.pptx'):
        filename += '.pptx'
        
    # Save the presentation
    _current_prs.save(filename)
    # Clear memory just in case
    _current_prs = None
    
    return f"Presentation successfully saved to {filename}"

if __name__ == "__main__":
    mcp.run()
