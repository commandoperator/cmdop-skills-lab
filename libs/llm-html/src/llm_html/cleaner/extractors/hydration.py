"""SSR Hydration payload extraction.

Extracts structured data from SSR frameworks BEFORE DOM parsing.
This is the most efficient way to reduce token counts for LLM processing.

Supported frameworks:
- Next.js Pages Router (__NEXT_DATA__)
- Next.js App Router (self.__next_f.push streaming)
- Nuxt 2 (window.__NUXT__)
- Nuxt 3 (__NUXT_DATA__ script tag)
- SvelteKit (__sveltekit_*)
- Remix (__remixContext)
- Gatsby (___gatsby)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, List, Tuple


class Framework(Enum):
    """Detected SSR framework."""
    UNKNOWN = "unknown"
    NEXTJS_PAGES = "nextjs_pages"
    NEXTJS_APP = "nextjs_app"
    NUXT2 = "nuxt2"
    NUXT3 = "nuxt3"
    SVELTEKIT = "sveltekit"
    REMIX = "remix"
    GATSBY = "gatsby"
    ASTRO = "astro"
    QWIK = "qwik"


@dataclass
class HydrationData:
    """Extracted hydration payload from SSR framework."""

    framework: Framework = Framework.UNKNOWN
    """Detected SSR framework."""

    version: Optional[str] = None
    """Framework version if detectable."""

    page_props: dict = field(default_factory=dict)
    """Main page data (pageProps, props, data, etc.)."""

    page_path: Optional[str] = None
    """Current page path/route."""

    build_id: Optional[str] = None
    """Build identifier for cache validation."""

    locale: Optional[str] = None
    """Detected locale/language."""

    raw_payload: Optional[str] = None
    """Original JSON string (for debugging)."""

    extraction_method: str = "none"
    """How data was extracted: script_tag, streaming, window_var."""

    success: bool = False
    """Whether extraction was successful."""

    error: Optional[str] = None
    """Error message if extraction failed."""

    @property
    def has_data(self) -> bool:
        """Check if meaningful data was extracted."""
        return bool(self.page_props) and self.success


# =============================================================================
# Detection Patterns
# =============================================================================

# Next.js Pages Router: <script id="__NEXT_DATA__" type="application/json">
NEXTJS_PAGES_PATTERN = re.compile(
    r'<script\s+id=["\']__NEXT_DATA__["\']\s+type=["\']application/json["\'][^>]*>'
    r'(.*?)</script>',
    re.DOTALL | re.IGNORECASE
)

# Next.js App Router: self.__next_f.push([...])
NEXTJS_APP_PATTERN = re.compile(
    r'self\.__next_f\.push\(\s*\[(.*?)\]\s*\)',
    re.DOTALL
)

# Nuxt 2: window.__NUXT__={...}
NUXT2_PATTERN = re.compile(
    r'window\.__NUXT__\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
    re.DOTALL
)

# Nuxt 3: <script type="application/json" id="__NUXT_DATA__">
NUXT3_PATTERN = re.compile(
    r'<script\s+[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE
)

# SvelteKit: __sveltekit_*
SVELTEKIT_PATTERN = re.compile(
    r'__sveltekit_\w+\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
    re.DOTALL
)

# Remix: window.__remixContext={...}
REMIX_PATTERN = re.compile(
    r'window\.__remixContext\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
    re.DOTALL
)

# Gatsby: window.___gatsby / window.__gatsby / pagePath
GATSBY_PATTERN = re.compile(
    r'window\.___?gatsby\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
    re.DOTALL
)

# Astro: Astro.props in script
ASTRO_PATTERN = re.compile(
    r'Astro\.props\s*=\s*(\{.+?\});?\s*(?:</script>|$)',
    re.DOTALL
)

# Qwik: <script type="qwik/json">
QWIK_PATTERN = re.compile(
    r'<script\s+type=["\']qwik/json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE
)


# =============================================================================
# Framework Detection
# =============================================================================

def detect_framework(html: str) -> Framework:
    """Detect SSR framework from HTML patterns.

    Args:
        html: Raw HTML string.

    Returns:
        Detected Framework enum value.
    """
    # Check in order of popularity/specificity

    # Next.js Pages Router
    if '__NEXT_DATA__' in html:
        return Framework.NEXTJS_PAGES

    # Next.js App Router (streaming)
    if 'self.__next_f.push' in html:
        return Framework.NEXTJS_APP

    # Nuxt 3 (check before Nuxt 2)
    if '__NUXT_DATA__' in html:
        return Framework.NUXT3

    # Nuxt 2
    if 'window.__NUXT__' in html or '__NUXT__' in html:
        return Framework.NUXT2

    # SvelteKit
    if '__sveltekit_' in html:
        return Framework.SVELTEKIT

    # Remix
    if '__remixContext' in html:
        return Framework.REMIX

    # Gatsby
    if '___gatsby' in html or '__gatsby' in html:
        return Framework.GATSBY

    # Qwik
    if 'type="qwik/json"' in html:
        return Framework.QWIK

    # Astro (less specific)
    if 'astro' in html.lower() and 'Astro.props' in html:
        return Framework.ASTRO

    return Framework.UNKNOWN


# =============================================================================
# Extraction Functions
# =============================================================================

def _safe_json_parse(json_str: str) -> Tuple[Optional[dict], Optional[str]]:
    """Safely parse JSON string.

    Args:
        json_str: JSON string to parse.

    Returns:
        Tuple of (parsed_data, error_message).
    """
    if not json_str:
        return None, "Empty JSON string"

    try:
        data = json.loads(json_str)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"


def _extract_nextjs_pages(html: str) -> HydrationData:
    """Extract Next.js Pages Router hydration data.

    Looks for: <script id="__NEXT_DATA__" type="application/json">
    """
    result = HydrationData(
        framework=Framework.NEXTJS_PAGES,
        extraction_method="script_tag"
    )

    match = NEXTJS_PAGES_PATTERN.search(html)
    if not match:
        result.error = "__NEXT_DATA__ script tag not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    # Extract relevant fields
    if isinstance(data, dict):
        result.success = True
        result.build_id = data.get("buildId")
        result.page_path = data.get("page")
        result.locale = data.get("locale")

        # Main data is in props.pageProps
        props = data.get("props", {})
        result.page_props = props.get("pageProps", props)

        # Try to detect version from runtimeConfig or other fields
        if "runtimeConfig" in data:
            result.version = "pages_router"

    return result


def _extract_nextjs_app(html: str) -> HydrationData:
    """Extract Next.js App Router hydration data.

    Aggregates streaming chunks from: self.__next_f.push([...])
    """
    result = HydrationData(
        framework=Framework.NEXTJS_APP,
        extraction_method="streaming"
    )

    matches = NEXTJS_APP_PATTERN.findall(html)
    if not matches:
        result.error = "No __next_f.push calls found"
        return result

    # Aggregate all chunks
    chunks = []
    for match in matches:
        try:
            # Each push contains an array like [type, data]
            # Try to extract the data part
            chunk_str = f"[{match}]"
            chunk_data = json.loads(chunk_str)
            chunks.append(chunk_data)
        except json.JSONDecodeError:
            # Try simpler extraction
            chunks.append(match)

    result.raw_payload = json.dumps(chunks)

    # Try to reconstruct the data
    # App Router streams data in specific format
    aggregated = {}
    for chunk in chunks:
        if isinstance(chunk, list) and len(chunk) >= 2:
            chunk_type = chunk[0]
            chunk_data = chunk[1] if len(chunk) > 1 else None

            if isinstance(chunk_data, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(chunk_data)
                    if isinstance(parsed, dict):
                        aggregated.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
            elif isinstance(chunk_data, dict):
                aggregated.update(chunk_data)

    if aggregated:
        result.success = True
        result.page_props = aggregated
        result.version = "app_router"
    else:
        # Return raw chunks if aggregation failed
        result.success = True
        result.page_props = {"_raw_chunks": chunks}

    return result


def _extract_nuxt2(html: str) -> HydrationData:
    """Extract Nuxt 2 hydration data.

    Looks for: window.__NUXT__={...}
    """
    result = HydrationData(
        framework=Framework.NUXT2,
        extraction_method="window_var"
    )

    match = NUXT2_PATTERN.search(html)
    if not match:
        result.error = "window.__NUXT__ not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, dict):
        result.success = True

        # Nuxt 2 structure: { data: [...], state: {...}, ... }
        nuxt_data = data.get("data", [])
        if isinstance(nuxt_data, list) and nuxt_data:
            # First item is usually the page data
            result.page_props = nuxt_data[0] if len(nuxt_data) == 1 else {"_items": nuxt_data}
        else:
            result.page_props = data

        result.version = "nuxt2"

    return result


def _extract_nuxt3(html: str) -> HydrationData:
    """Extract Nuxt 3 hydration data.

    Looks for: <script type="application/json" id="__NUXT_DATA__">
    """
    result = HydrationData(
        framework=Framework.NUXT3,
        extraction_method="script_tag"
    )

    match = NUXT3_PATTERN.search(html)
    if not match:
        result.error = "__NUXT_DATA__ script tag not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, (dict, list)):
        result.success = True
        result.page_props = data if isinstance(data, dict) else {"_items": data}
        result.version = "nuxt3"

    return result


def _extract_sveltekit(html: str) -> HydrationData:
    """Extract SvelteKit hydration data."""
    result = HydrationData(
        framework=Framework.SVELTEKIT,
        extraction_method="window_var"
    )

    match = SVELTEKIT_PATTERN.search(html)
    if not match:
        result.error = "__sveltekit_* not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, dict):
        result.success = True
        result.page_props = data.get("data", data)
        result.version = "sveltekit"

    return result


def _extract_remix(html: str) -> HydrationData:
    """Extract Remix hydration data."""
    result = HydrationData(
        framework=Framework.REMIX,
        extraction_method="window_var"
    )

    match = REMIX_PATTERN.search(html)
    if not match:
        result.error = "__remixContext not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, dict):
        result.success = True
        # Remix structure: { state: { loaderData: {...} } }
        state = data.get("state", {})
        loader_data = state.get("loaderData", {})
        result.page_props = loader_data if loader_data else data
        result.version = "remix"

    return result


def _extract_gatsby(html: str) -> HydrationData:
    """Extract Gatsby hydration data."""
    result = HydrationData(
        framework=Framework.GATSBY,
        extraction_method="window_var"
    )

    match = GATSBY_PATTERN.search(html)
    if not match:
        result.error = "___gatsby not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, dict):
        result.success = True
        result.page_props = data
        result.version = "gatsby"

    return result


def _extract_qwik(html: str) -> HydrationData:
    """Extract Qwik hydration data."""
    result = HydrationData(
        framework=Framework.QWIK,
        extraction_method="script_tag"
    )

    match = QWIK_PATTERN.search(html)
    if not match:
        result.error = "qwik/json script not found"
        return result

    json_str = match.group(1).strip()
    result.raw_payload = json_str

    data, error = _safe_json_parse(json_str)
    if error:
        result.error = error
        return result

    if isinstance(data, (dict, list)):
        result.success = True
        result.page_props = data if isinstance(data, dict) else {"_items": data}
        result.version = "qwik"

    return result


# =============================================================================
# Main Extractor Class
# =============================================================================

class HydrationExtractor:
    """Extract SSR hydration data from HTML.

    This should be called BEFORE any DOM parsing/cleaning.
    If hydration data is found, it can often replace DOM parsing entirely.

    Example:
        extractor = HydrationExtractor()
        result = extractor.extract(html)

        if result.has_data:
            # Use result.page_props directly - no DOM parsing needed!
            products = result.page_props.get("products", [])
        else:
            # Fall back to DOM-based cleaning
            cleaned = HTMLCleaner().clean_aggressive(html)
    """

    # Map framework to extraction function
    EXTRACTORS = {
        Framework.NEXTJS_PAGES: _extract_nextjs_pages,
        Framework.NEXTJS_APP: _extract_nextjs_app,
        Framework.NUXT2: _extract_nuxt2,
        Framework.NUXT3: _extract_nuxt3,
        Framework.SVELTEKIT: _extract_sveltekit,
        Framework.REMIX: _extract_remix,
        Framework.GATSBY: _extract_gatsby,
        Framework.QWIK: _extract_qwik,
    }

    def extract(self, html: str, framework: Framework = None) -> HydrationData:
        """Extract hydration data from HTML.

        Args:
            html: Raw HTML string.
            framework: Optional framework hint. If None, auto-detects.

        Returns:
            HydrationData with extracted data or error info.
        """
        if not html:
            return HydrationData(error="Empty HTML")

        # Detect framework if not provided
        if framework is None:
            framework = detect_framework(html)

        if framework == Framework.UNKNOWN:
            return HydrationData(
                framework=Framework.UNKNOWN,
                error="No known SSR framework detected"
            )

        # Get appropriate extractor
        extractor = self.EXTRACTORS.get(framework)
        if not extractor:
            return HydrationData(
                framework=framework,
                error=f"No extractor for {framework.value}"
            )

        # Extract data
        return extractor(html)

    def extract_all(self, html: str) -> List[HydrationData]:
        """Try all extractors and return all successful results.

        Useful when page might have multiple SSR payloads.

        Args:
            html: Raw HTML string.

        Returns:
            List of successful HydrationData extractions.
        """
        results = []

        for framework, extractor in self.EXTRACTORS.items():
            try:
                result = extractor(html)
                if result.success:
                    results.append(result)
            except Exception:
                pass

        return results


# =============================================================================
# Convenience Functions
# =============================================================================

def extract_hydration(html: str) -> HydrationData:
    """Extract hydration data from HTML (convenience function).

    Args:
        html: Raw HTML string.

    Returns:
        HydrationData with extracted data.
    """
    return HydrationExtractor().extract(html)
