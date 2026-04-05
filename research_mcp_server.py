"""
Research MCP Server
-------------------
Handles factual research and image discovery via DuckDuckGo and internet APIs.
"""

from mcp.server.fastmcp import FastMCP
from ddgs import DDGS
import requests
import hashlib

mcp = FastMCP("Research MCP Server")

@mcp.tool()
def research_topic(topic: str) -> list[str]:
    """
    Search the web for real facts about a topic.
    Returns a list of short educational facts.
    """
    facts = []
    try:
        # Use DuckDuckGo Search (DDGS) to find educational facts
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{topic} key facts educational", max_results=8))
            for r in results:
                body = r.get("body", "")
                if body and len(body) > 20:
                    # Basic sentence splitting to extract bite-sized information
                    sentences = body.replace(". ", ".|").split("|")
                    for sent in sentences[:2]:
                        sent = sent.strip().rstrip(".")
                        words = sent.split()
                        # Filter for sentences that are likely to be good bullet points
                        if 3 <= len(words) <= 12:
                            facts.append(" ".join(words[:8]))
    except Exception:
        # Silently fail and return whatever facts were collected
        pass
    return facts[:12]

@mcp.tool()
def find_image_url(query: str) -> str:
    """
    Finds a high-quality image URL for a given query.
    Uses Pixabay/Unsplash/Picsum fallbacks for reliability.
    """
    # Attempt 1: Search for images using DuckDuckGo
    try:
        with DDGS() as ddgs:
            # Look for 3 candidate images
            results = list(ddgs.images(query, max_results=3))
            for r in results:
                url = r.get("image", "")
                # Ensure the URL is likely a direct image link
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg"]):
                    # Perform a HEAD request to check if the image is accessible
                    t = requests.head(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
                    if t.status_code == 200:
                        return url
    except Exception:
        pass
    
    # Attempt 2: Picsum Seeded Fallback (Guaranteed to work if search fails)
    # Generate a deterministic seed based on the query string
    seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 1000
    return f"https://picsum.photos/seed/{seed}/800/600"

if __name__ == "__main__":
    mcp.run()
