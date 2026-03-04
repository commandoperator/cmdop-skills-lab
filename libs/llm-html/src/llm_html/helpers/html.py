"""HTML utilities for text extraction."""

from __future__ import annotations

from bs4 import BeautifulSoup


def html_to_text(html: str, separator: str = "\n") -> str:
    """
    Convert HTML to plain text.

    Args:
        html: HTML string
        separator: Separator between text blocks (default: newline)

    Returns:
        Plain text with separator between blocks.

    Usage:
        text = html_to_text("<div><p>Hello</p><p>World</p></div>")
        # "Hello\nWorld"
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "lxml")

    # Remove script and style elements
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    # Get text, handling whitespace
    text = soup.get_text(separator=separator, strip=True)

    # Clean up multiple separators
    if separator == "\n":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    return text


def extract_links(html: str, base_url: str = "") -> list[dict]:
    """
    Extract all links from HTML.

    Args:
        html: HTML string
        base_url: Base URL to resolve relative links

    Returns:
        List of dicts with 'url', 'text' keys.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not isinstance(href, str):
            continue
        if base_url and not href.startswith(("http://", "https://", "//")):
            href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
        elif href.startswith("//"):
            href = f"https:{href}"

        links.append({
            "url": href,
            "text": a.get_text(strip=True),
        })

    return links


def extract_images(html: str, base_url: str = "") -> list[str]:
    """
    Extract all image URLs from HTML.

    Args:
        html: HTML string
        base_url: Base URL to resolve relative links

    Returns:
        List of image URLs.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    images = []

    for img in soup.find_all("img", src=True):
        src = img["src"]
        if not isinstance(src, str):
            continue
        if base_url and not src.startswith(("http://", "https://", "//")):
            src = f"{base_url.rstrip('/')}/{src.lstrip('/')}"
        elif src.startswith("//"):
            src = f"https:{src}"
        images.append(src)

    return images
