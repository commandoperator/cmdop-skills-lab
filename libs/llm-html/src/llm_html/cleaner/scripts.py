"""JSON script detection and extraction utilities."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from bs4 import Tag

from .config import JSON_SCRIPT_TYPES, SSR_SCRIPT_INDICATORS


@dataclass
class ExtractedData:
    """Extracted structured data from HTML scripts."""

    ssr_data: dict = field(default_factory=dict)
    """SSR data from Next.js, Nuxt.js, etc."""

    structured_data: list = field(default_factory=list)
    """JSON-LD schema.org data."""

    product_data: dict = field(default_factory=dict)
    """E-commerce product data."""

    page_data: dict = field(default_factory=dict)
    """Generic page data."""


def is_json_script(script: Tag) -> bool:
    """Check if a script tag contains valuable JSON data.

    Args:
        script: BeautifulSoup Tag object for a script element.

    Returns:
        True if the script contains JSON data that should be preserved.
    """
    if script.name != "script":
        return False

    # 1. Check script type attribute
    script_type = script.get("type")
    if script_type:
        script_type_str = str(script_type).lower()
        if script_type_str in JSON_SCRIPT_TYPES:
            return True

    # 2. Check ID for SSR framework indicators
    script_id = script.get("id")
    script_id_str = str(script_id).lower() if script_id else ""
    for indicator in SSR_SCRIPT_INDICATORS:
        if indicator in script_id_str:
            return True

    # 3. Check content for JSON-LD pattern
    content = script.get_text().strip()
    if not content:
        return False

    # Check for JSON-LD context
    if '"@context"' in content or "'@context'" in content:
        return True

    # 4. Try to parse as JSON (limit size to avoid slow parsing)
    if len(content) > 100_000:  # 100KB limit
        return False

    if content.startswith("{") and content.endswith("}"):
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            pass

    if content.startswith("[") and content.endswith("]"):
        try:
            json.loads(content)
            return True
        except (json.JSONDecodeError, ValueError):
            pass

    return False


def extract_json_from_script(script: Tag) -> Optional[Any]:
    """Extract JSON data from a script tag.

    Args:
        script: BeautifulSoup Tag object for a script element.

    Returns:
        Parsed JSON data, or None if parsing fails.
    """
    content = script.get_text().strip()
    if not content:
        return None

    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return None


def extract_ssr_data(html: str) -> dict:
    """Extract SSR framework data from HTML string.

    Looks for patterns like:
    - __NEXT_DATA__ = {...}
    - __NUXT__ = {...}
    - window.__INITIAL_STATE__ = {...}

    Args:
        html: Raw HTML string.

    Returns:
        Dictionary with framework name as key and parsed data as value.
    """
    patterns = [
        (r"__NEXT_DATA__\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "next"),
        (r"__NUXT__\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "nuxt"),
        (r"__SVELTEKIT__\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "sveltekit"),
        (r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "initial_state"),
        (r"window\.__REACT_QUERY_STATE__\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "react_query"),
        (r"window\.productData\s*=\s*(\{.+?\});?\s*(?:</script>|$)", "product"),
    ]

    result = {}
    for pattern, name in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                result[name] = data
            except (json.JSONDecodeError, ValueError):
                pass

    return result


def extract_structured_data_from_soup(soup) -> list:
    """Extract JSON-LD structured data from BeautifulSoup object.

    Args:
        soup: BeautifulSoup object.

    Returns:
        List of parsed JSON-LD objects.
    """
    result = []

    for script in soup.find_all("script", type="application/ld+json"):
        data = extract_json_from_script(script)
        if data:
            if isinstance(data, list):
                result.extend(data)
            else:
                result.append(data)

    return result


def extract_all_data(soup, html: str = "") -> ExtractedData:
    """Extract all valuable data from HTML.

    Args:
        soup: BeautifulSoup object.
        html: Optional raw HTML string for SSR pattern matching.

    Returns:
        ExtractedData object with all extracted data.
    """
    extracted = ExtractedData()

    # Extract JSON-LD structured data
    extracted.structured_data = extract_structured_data_from_soup(soup)

    # Extract SSR data from raw HTML
    if html:
        extracted.ssr_data = extract_ssr_data(html)

    # Try to extract product data from common scripts
    for script in soup.find_all("script", id=re.compile(r"product|item", re.I)):
        data = extract_json_from_script(script)
        if data:
            extracted.product_data.update(data if isinstance(data, dict) else {"items": data})

    return extracted
