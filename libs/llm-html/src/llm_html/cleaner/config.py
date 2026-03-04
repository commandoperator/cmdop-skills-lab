"""HTML Cleaner configuration constants and patterns."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Set, List, Pattern


# =============================================================================
# Size Limits
# =============================================================================
MAX_HTML_SIZE = 2_000_000      # 2MB max input
MAX_URL_LENGTH = 200           # Truncate URLs longer than this
MAX_ATTRIBUTE_LENGTH = 500     # Truncate attribute values longer than this
MAX_TEXT_LENGTH_STAGE1 = 500   # Text truncation for Stage 1 (aggressive)
MAX_TEXT_LENGTH_STAGE2 = 1000  # Text truncation for Stage 2 (focused)

# =============================================================================
# Context Preservation
# =============================================================================
CONTEXT_RADIUS = 3             # Parent levels to preserve around selected elements
MAX_PRESERVED_CHILDREN = 20    # Max children to preserve per element
MAX_EMPTY_ITERATIONS = 5       # Max passes for empty element removal

# =============================================================================
# Selection Marker
# =============================================================================
SELECTION_MARKER_ATTR = "data-cmdop-id"


# =============================================================================
# Tags to Remove
# =============================================================================

# Aggressive mode: maximum compression
AGGRESSIVE_NOISE_TAGS: Set[str] = {
    # Scripts and styles
    "script", "style", "link", "noscript",
    # Media and embeds
    "iframe", "embed", "object", "canvas", "video", "audio",
    "source", "track", "param",
    # SVG elements
    "svg", "path", "use", "defs", "clippath", "mask", "pattern",
    "lineargradient", "radialgradient", "circle", "rect", "ellipse",
    "line", "polyline", "polygon", "g",
    # Structure
    "template", "datalist", "base",
    # Less important content (aggressive only)
    "form", "aside", "footer", "header", "nav",
}

# Focused mode: preserve more structure
FOCUSED_NOISE_TAGS: Set[str] = {
    # Scripts and styles only
    "script", "style", "link", "noscript",
    # Embeds
    "iframe", "embed", "object", "canvas",
    # Structure
    "template", "datalist", "base",
}

# Void elements (never removed as "empty")
VOID_ELEMENTS: Set[str] = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# Tags to check for empty removal
EMPTY_REMOVAL_TAGS: List[str] = [
    "div", "span", "p", "section", "article", "aside", "header",
    "footer", "nav", "main", "figure", "figcaption", "ul", "ol", "li",
]


# =============================================================================
# Attributes
# =============================================================================

# Attributes to always remove
REMOVE_ATTRIBUTES: Set[str] = {
    # Styling
    "style",
    # Event handlers
    "onclick", "onload", "onerror", "onchange", "onmouseover", "onmouseout",
    "onfocus", "onblur", "onsubmit", "onreset", "onabort", "onkeydown",
    "onkeyup", "onkeypress", "ondblclick", "onmousedown", "onmouseup",
    "onmousemove", "oncontextmenu", "onwheel", "ondrag", "ondrop",
    "onscroll", "onresize", "ontouchstart", "ontouchend", "ontouchmove",
    # Tracking
    "data-gtm", "data-analytics", "data-tracking", "data-ga", "data-fb",
    "data-pixel", "data-track",
    # Form/misc
    "autocomplete", "autofocus", "spellcheck", "contenteditable",
    "draggable", "hidden", "loading", "decoding", "fetchpriority",
    "crossorigin", "integrity", "referrerpolicy", "sizes", "media",
    "as", "defer", "async", "nomodule",
}

# Attributes to always keep
KEEP_ATTRIBUTES: Set[str] = {
    "id", "class", "href", "src", "alt", "title", "name", "value",
    "type", "role", "lang", "placeholder", "for", "action", "method",
    "target", "rel", "itemscope", "itemtype", "itemid", "itemprop",
    # Accessibility
    "aria-label", "aria-labelledby", "aria-describedby", "aria-hidden",
    # Testing
    "data-testid", "data-test", "data-cy",
    # Plugin marker
    SELECTION_MARKER_ATTR,
}

# Attribute patterns to keep (prefix matching)
KEEP_ATTRIBUTE_PREFIXES: List[str] = [
    "data-cmdop",
    "aria-",
    "itemscope",
    "itemtype",
    "itemprop",
]


# =============================================================================
# Noise Selectors (CSS)
# =============================================================================

NOISE_SELECTORS: List[str] = [
    # Cookie/privacy banners
    ".cookie-banner", ".cookie-notice", ".gdpr-notice", ".gdpr-banner",
    ".privacy-notice", ".consent-banner", "#cookie-banner", "#cookie-notice",
    "#gdpr-notice", "#privacy-notice", "[class*='cookie']", "[class*='gdpr']",
    # Advertisements
    ".advertisement", ".ads", ".ad-container", ".sponsored", ".promo",
    "[class*='advertisement']", "[class*='sponsored']",
    # Popups/modals
    ".popup", ".modal", ".modal-overlay", ".overlay", ".lightbox",
    "[class*='popup']", "[class*='modal']",
    # Social
    ".social-share", ".share-buttons", ".social-widget",
    "[class*='social-share']", "[class*='share-button']",
    # Navigation noise
    ".breadcrumb", ".breadcrumbs", ".pagination",
    # Loading indicators
    ".loading", ".spinner", ".skeleton", ".placeholder",
    # Tracking
    "[class*='analytics']", "[class*='tracking']", "[class*='gtm-']",
    "[data-ad]", "[data-tracking]",
]


# =============================================================================
# JSON Scripts
# =============================================================================

# Script types that contain valuable JSON data
JSON_SCRIPT_TYPES: Set[str] = {
    "application/ld+json",
    "application/json",
    "text/json",
    "application/settings+json",
    "application/manifest+json",
}

# SSR framework script ID indicators
SSR_SCRIPT_INDICATORS: List[str] = [
    "__next_data__",
    "__nuxt__",
    "__sveltekit__",
    "gatsby-chunk-mapping",
    "webpack-manifest",
    "app-data",
    "initial-state",
    "structured-data",
    "__apollo_state__",
    "__relay_store__",
]


# =============================================================================
# CSS Class Patterns
# =============================================================================

# Hash patterns (auto-generated classes to REMOVE)
HASH_CLASS_PATTERNS: List[Pattern] = [
    re.compile(r'^x[a-z0-9]{6,}$', re.IGNORECASE),         # Facebook
    re.compile(r'^_[a-z0-9]{4,}$', re.IGNORECASE),          # CSS modules
    re.compile(r'^css-[a-z0-9]+$', re.IGNORECASE),          # styled-components
    re.compile(r'^sc-[a-z0-9-]+$', re.IGNORECASE),          # styled-components
    re.compile(r'^jsx-[0-9]+$', re.IGNORECASE),             # JSX
    re.compile(r'^emotion-[a-z0-9]+$', re.IGNORECASE),      # Emotion CSS
    re.compile(r'^MuiBox-[a-zA-Z0-9-]+$', re.IGNORECASE),   # Material-UI
    re.compile(r'^chakra-[a-z0-9-]+$', re.IGNORECASE),      # Chakra UI
    re.compile(r'^ant-[a-z0-9-]+$', re.IGNORECASE),         # Ant Design
    re.compile(r'^jss[0-9]+$', re.IGNORECASE),              # JSS
    re.compile(r'^makeStyles-[a-zA-Z0-9]+$', re.IGNORECASE),# MUI makeStyles
    re.compile(r'^[a-f0-9]{8,}$', re.IGNORECASE),           # Pure hash
]

# Semantic patterns (classes to KEEP)
SEMANTIC_CLASS_PATTERNS: List[Pattern] = [
    re.compile(r'^(header|footer|main|nav|aside|section|article)$', re.IGNORECASE),
    re.compile(r'^(title|heading|content|description|summary|body)$', re.IGNORECASE),
    re.compile(r'^(product|item|card|post|comment|review|listing)$', re.IGNORECASE),
    re.compile(r'^(price|cost|amount|value|rating|score|quantity)$', re.IGNORECASE),
    re.compile(r'^(form|input|button|submit|search|login|signup)$', re.IGNORECASE),
    re.compile(r'^(menu|list|table|row|cell|column|grid)$', re.IGNORECASE),
    re.compile(r'^(image|photo|video|media|gallery|thumbnail)$', re.IGNORECASE),
    re.compile(r'^(active|selected|current|highlighted|disabled)$', re.IGNORECASE),
    re.compile(r'^(error|warning|success|info|alert|message)$', re.IGNORECASE),
    re.compile(r'^(container|wrapper|layout|content|body|inner)$', re.IGNORECASE),
]

# Utility class patterns to REMOVE (Tailwind, Bootstrap)
UTILITY_CLASS_PATTERNS: List[Pattern] = [
    re.compile(r'^(m|p|mt|mb|ml|mr|mx|my|pt|pb|pl|pr|px|py)-\d+$', re.IGNORECASE),
    re.compile(r'^(w|h|min-w|min-h|max-w|max-h)-\d+$', re.IGNORECASE),
    re.compile(r'^(text|bg|border|rounded)-\w+$', re.IGNORECASE),
    re.compile(r'^(flex|grid|block|inline|hidden)$', re.IGNORECASE),
    re.compile(r'^(col|row)-\d+$', re.IGNORECASE),
]


# =============================================================================
# Tracking URL Patterns
# =============================================================================

TRACKING_URL_PATTERNS: List[Pattern] = [
    re.compile(r'google-analytics\.com', re.IGNORECASE),
    re.compile(r'googletagmanager\.com', re.IGNORECASE),
    re.compile(r'facebook\.com/tr', re.IGNORECASE),
    re.compile(r'doubleclick\.net', re.IGNORECASE),
    re.compile(r'googlesyndication\.com', re.IGNORECASE),
    re.compile(r'amazon-adsystem\.com', re.IGNORECASE),
    re.compile(r'/analytics', re.IGNORECASE),
    re.compile(r'/tracking', re.IGNORECASE),
    re.compile(r'/pixel', re.IGNORECASE),
    re.compile(r'/gtm\.js', re.IGNORECASE),
]


# =============================================================================
# HTML Entities
# =============================================================================

# Entities to protect during decoding (structural)
PROTECTED_ENTITIES = {
    "&lt;": "__PROTECTED_LT__",
    "&gt;": "__PROTECTED_GT__",
    "&amp;": "__PROTECTED_AMP__",
    "&quot;": "__PROTECTED_QUOT__",
    "&apos;": "__PROTECTED_APOS__",
}

# Common named entities to decode
COMMON_ENTITIES = {
    "&nbsp;": " ",
    "&ndash;": "-",
    "&mdash;": "--",
    "&lsquo;": "'",
    "&rsquo;": "'",
    "&ldquo;": '"',
    "&rdquo;": '"',
    "&hellip;": "...",
    "&copy;": "(c)",
    "&reg;": "(R)",
    "&trade;": "(TM)",
    "&euro;": "EUR",
    "&pound;": "GBP",
    "&yen;": "JPY",
    "&cent;": "c",
}


# =============================================================================
# Configuration Dataclass
# =============================================================================

@dataclass
class CleaningConfig:
    """Configuration for HTML cleaning operations."""

    # Size limits
    max_html_size: int = MAX_HTML_SIZE
    max_url_length: int = MAX_URL_LENGTH
    max_attribute_length: int = MAX_ATTRIBUTE_LENGTH
    max_text_length: int = MAX_TEXT_LENGTH_STAGE1

    # Context preservation
    context_radius: int = CONTEXT_RADIUS
    max_preserved_children: int = MAX_PRESERVED_CHILDREN
    max_empty_iterations: int = MAX_EMPTY_ITERATIONS

    # Cleaning options
    remove_scripts: bool = True
    remove_styles: bool = True
    remove_svg: bool = True
    clean_attributes: bool = True
    clean_classes: bool = True
    clean_tracking_urls: bool = True
    clean_base64: bool = True
    decode_entities: bool = True
    remove_empty: bool = True
    remove_comments: bool = True

    # Tags to remove
    noise_tags: Set[str] = field(default_factory=lambda: AGGRESSIVE_NOISE_TAGS.copy())
    noise_selectors: List[str] = field(default_factory=lambda: NOISE_SELECTORS.copy())

    # Preserved selectors
    preserve_selectors: List[str] = field(default_factory=list)


@dataclass
class FocusedCleaningConfig(CleaningConfig):
    """Configuration for Stage 2 focused cleaning."""

    max_text_length: int = MAX_TEXT_LENGTH_STAGE2
    noise_tags: Set[str] = field(default_factory=lambda: FOCUSED_NOISE_TAGS.copy())
    preserve_plugin_elements: bool = True
