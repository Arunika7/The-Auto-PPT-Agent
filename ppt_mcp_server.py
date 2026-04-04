"""
PowerPoint MCP Server — Multi-Agent V2
---------------------------------------
Design-aware MCP tool server with:
- 6 predefined theme palettes (space, business, education, tech, nature, medical)
- 4 layout engines (text_only, text_left_image_right, image_background, title_only)
- Mermaid diagram → PNG rendering via mermaid.ink API
- Internet image downloading and embedding
"""

from mcp.server.fastmcp import FastMCP
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os
import requests
import base64
from io import BytesIO

# ──────────────────────────────────────────────
# DESIGN SYSTEM: Theme Palettes
# ──────────────────────────────────────────────
THEMES = {
    "space":     {"bg": "#0f0235", "title": "#c084fc", "text": "#e0e7ff", "accent": "#7c3aed"},
    "business":  {"bg": "#1e293b", "title": "#60a5fa", "text": "#e2e8f0", "accent": "#3b82f6"},
    "education": {"bg": "#1a1a2e", "title": "#fbbf24", "text": "#fef3c7", "accent": "#f59e0b"},
    "tech":      {"bg": "#0c0a09", "title": "#22d3ee", "text": "#d4d4d8", "accent": "#06b6d4"},
    "nature":    {"bg": "#052e16", "title": "#86efac", "text": "#dcfce7", "accent": "#22c55e"},
    "medical":   {"bg": "#1e1b4b", "title": "#a78bfa", "text": "#e0e7ff", "accent": "#8b5cf6"},
}

def _hex_to_rgb(hex_str: str) -> RGBColor:
    """Convert '#RRGGBB' string to python-pptx RGBColor."""
    h = hex_str.lstrip('#')
    if len(h) != 6:
        h = "1E1E2E"
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def _resolve_theme(theme: str) -> dict:
    """Resolve a theme name to its color palette dict. Falls back to 'space'."""
    return THEMES.get(theme.lower().strip(), THEMES["space"])

def _set_background(slide, hex_color: str):
    """Apply a solid background color to a slide."""
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = _hex_to_rgb(hex_color)

def _download_image(url: str) -> BytesIO | None:
    """Download an image from URL, return BytesIO stream or None on failure."""
    try:
        resp = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        if len(resp.content) < 500:  # Too small = probably an error page
            return None
        return BytesIO(resp.content)
    except Exception:
        return None

def _render_mermaid_png(mermaid_code: str) -> BytesIO | None:
    """Convert Mermaid code to PNG via the free mermaid.ink API."""
    try:
        encoded = base64.urlsafe_b64encode(mermaid_code.encode("utf-8")).decode("ascii")
        url = f"https://mermaid.ink/img/{encoded}?bgColor=!0f0235"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return BytesIO(resp.content)
    except Exception:
        return None

# ──────────────────────────────────────────────
# MCP SERVER INITIALIZATION
# ──────────────────────────────────────────────
mcp = FastMCP("PowerPoint MCP Server")
_current_prs = None

@mcp.tool()
def create_presentation() -> str:
    """Initializes a new blank 16:9 widescreen PowerPoint presentation in memory."""
    global _current_prs
    _current_prs = Presentation()
    _current_prs.slide_width = Inches(13.333)
    _current_prs.slide_height = Inches(7.5)
    return "New blank 16:9 presentation created in memory."

@mcp.tool()
def add_title_slide(title: str, subtitle: str, theme: str = "space") -> str:
    """
    Adds a cinematic title slide (first slide of the presentation).
    Args:
        title: The main title text (keep it short).
        subtitle: The subtitle text below.
        theme: Theme name (space, business, education, tech, nature, medical).
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists. Call create_presentation first."
    
    colors = _resolve_theme(theme)
    slide = _current_prs.slides.add_slide(_current_prs.slide_layouts[6])  # Blank layout
    _set_background(slide, colors["bg"])
    
    # Title — large, centered
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.3), Inches(1.8))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = "Segoe UI"
    p.font.size = Pt(54)
    p.font.color.rgb = _hex_to_rgb(colors["title"])
    p.font.bold = True
    p.alignment = PP_ALIGN.CENTER
    
    # Subtitle
    sub_box = slide.shapes.add_textbox(Inches(2), Inches(4.2), Inches(9.3), Inches(1))
    tf2 = sub_box.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(24)
    p2.font.color.rgb = _hex_to_rgb(colors["text"])
    p2.alignment = PP_ALIGN.CENTER
    
    # Accent bar
    accent_bar = slide.shapes.add_shape(
        1, Inches(4.5), Inches(3.9), Inches(4.3), Inches(0.06)  # MSO_SHAPE.RECTANGLE = 1
    )
    accent_bar.fill.solid()
    accent_bar.fill.fore_color.rgb = _hex_to_rgb(colors["accent"])
    accent_bar.line.fill.background()
    
    return f"Title slide '{title}' added."

@mcp.tool()
def add_slide(title: str, bullet_points: list[str], layout_type: str = "text_only",
              image_url: str = "", theme: str = "space") -> str:
    """
    Adds a content slide with flexible layout.
    Args:
        title: Slide title (max 6 words).
        bullet_points: List of short bullet strings (max 4 items, max 6 words each).
        layout_type: One of 'text_only', 'text_left_image_right', 'image_background', 'title_only'.
        image_url: Direct URL to a .jpg/.png image (required for image layouts, optional otherwise).
        theme: Theme name for colors.
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists."
    
    colors = _resolve_theme(theme)
    slide = _current_prs.slides.add_slide(_current_prs.slide_layouts[6])  # Blank layout
    _set_background(slide, colors["bg"])
    
    # Download image if provided
    img_stream = None
    if image_url and image_url.strip():
        img_stream = _download_image(image_url.strip())
    
    # ── LAYOUT: title_only ──
    if layout_type == "title_only":
        box = slide.shapes.add_textbox(Inches(1.5), Inches(2.5), Inches(10.3), Inches(2))
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "Segoe UI"
        p.font.size = Pt(48)
        p.font.color.rgb = _hex_to_rgb(colors["title"])
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        return f"Title-only slide '{title}' added."
    
    # ── LAYOUT: image_background ──
    if layout_type == "image_background" and img_stream:
        slide.shapes.add_picture(img_stream, Inches(0), Inches(0),
                                  width=Inches(13.333), height=Inches(7.5))
        # Dark overlay textbox
        overlay = slide.shapes.add_shape(1, Inches(0), Inches(4.5), Inches(13.333), Inches(3))
        overlay.fill.solid()
        overlay.fill.fore_color.rgb = RGBColor(0, 0, 0)
        # Set transparency via XML hack
        from pptx.oxml.ns import qn
        solidFill = overlay.fill._fill
        srgb = solidFill.find(qn("a:solidFill")).find(qn("a:srgbClr"))
        if srgb is not None:
            alpha = srgb.makeelement(qn("a:alpha"), {"val": "45000"})
            srgb.append(alpha)
        overlay.line.fill.background()
        
        # Title over image
        t_box = slide.shapes.add_textbox(Inches(0.8), Inches(4.7), Inches(11.7), Inches(1))
        tf = t_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "Segoe UI"
        p.font.size = Pt(40)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.bold = True
        
        # Bullets over image
        if bullet_points:
            b_box = slide.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.7), Inches(1.5))
            btf = b_box.text_frame
            btf.word_wrap = True
            for i, bp in enumerate(bullet_points[:4]):
                para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
                para.text = f"  •  {bp}"
                para.font.name = "Segoe UI"
                para.font.size = Pt(20)
                para.font.color.rgb = RGBColor(230, 230, 230)
        
        return f"Image-background slide '{title}' added."
    
    # ── LAYOUT: text_left_image_right ──
    if layout_type == "text_left_image_right" and img_stream:
        # Title — full width top
        t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1))
        tf = t_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "Segoe UI"
        p.font.size = Pt(38)
        p.font.color.rgb = _hex_to_rgb(colors["title"])
        p.font.bold = True
        
        # Bullets — left 55%
        b_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(6.2), Inches(5))
        btf = b_box.text_frame
        btf.word_wrap = True
        for i, bp in enumerate(bullet_points[:4]):
            para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
            para.text = f"•  {bp}"
            para.font.name = "Segoe UI"
            para.font.size = Pt(22)
            para.font.color.rgb = _hex_to_rgb(colors["text"])
            para.space_after = Pt(14)
        
        # Image — right 45%
        try:
            slide.shapes.add_picture(img_stream, Inches(7.5), Inches(1.5), width=Inches(5.3), height=Inches(4.8))
        except Exception:
            pass  # Graceful degradation
        
        return f"Text+image slide '{title}' added."
    
    # ── LAYOUT: text_only (default fallback) ──
    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1))
    tf = t_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = "Segoe UI"
    p.font.size = Pt(38)
    p.font.color.rgb = _hex_to_rgb(colors["title"])
    p.font.bold = True
    
    # Bullets — centered wider
    b_box = slide.shapes.add_textbox(Inches(1.2), Inches(2.0), Inches(10.9), Inches(4.5))
    btf = b_box.text_frame
    btf.word_wrap = True
    for i, bp in enumerate(bullet_points[:4]):
        para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
        para.text = f"•  {bp}"
        para.font.name = "Segoe UI"
        para.font.size = Pt(24)
        para.font.color.rgb = _hex_to_rgb(colors["text"])
        para.space_after = Pt(18)
    
    # If image available, add it bottom-right as accent
    if img_stream:
        try:
            slide.shapes.add_picture(img_stream, Inches(8.5), Inches(4.5), height=Inches(2.5))
        except Exception:
            pass
    
    return f"Text slide '{title}' added with {len(bullet_points)} bullets."

@mcp.tool()
def add_diagram_slide(title: str, mermaid_code: str, theme: str = "space") -> str:
    """
    Renders a Mermaid.js diagram to PNG and embeds it into a new slide.
    Args:
        title: Slide title.
        mermaid_code: Raw Mermaid diagram code (e.g., 'flowchart LR ...').
        theme: Theme name for background colors.
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists."
    
    colors = _resolve_theme(theme)
    
    # Render via mermaid.ink
    img_stream = _render_mermaid_png(mermaid_code)
    if img_stream is None:
        return f"Error: Could not render Mermaid diagram. Code: {mermaid_code[:100]}"
    
    slide = _current_prs.slides.add_slide(_current_prs.slide_layouts[6])  # Blank
    _set_background(slide, colors["bg"])
    
    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.3), Inches(11.7), Inches(1))
    tf = t_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = "Segoe UI"
    p.font.size = Pt(36)
    p.font.color.rgb = _hex_to_rgb(colors["title"])
    p.font.bold = True
    
    # Diagram — centered
    try:
        slide.shapes.add_picture(img_stream, Inches(1.5), Inches(1.5), width=Inches(10.3), height=Inches(5.2))
    except Exception as e:
        return f"Error embedding diagram image: {str(e)}"
    
    return f"Diagram slide '{title}' added."

@mcp.tool()
def save_presentation(filename: str) -> str:
    """
    Saves the in-memory presentation to the local disk.
    Args:
        filename: The output filename (auto-overridden to sync with UI).
    """
    global _current_prs
    if _current_prs is None:
        return "Error: No presentation exists to save."
    
    filename = "output_presentation.pptx"
    _current_prs.save(filename)
    return f"Presentation saved to {filename}"

if __name__ == "__main__":
    mcp.run()
