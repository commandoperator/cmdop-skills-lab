"""Data extractors for HTML preprocessing."""
from .hydration import (
    HydrationExtractor,
    HydrationData,
    Framework,
    extract_hydration,
    detect_framework,
)
from .context import (
    ContextExtractor,
    ContextWindow,
    ContextConfig,
    extract_context,
    find_stable_anchor,
    generate_selector,
)

__all__ = [
    # Hydration
    "HydrationExtractor",
    "HydrationData",
    "Framework",
    "extract_hydration",
    "detect_framework",
    # Context Window
    "ContextExtractor",
    "ContextWindow",
    "ContextConfig",
    "extract_context",
    "find_stable_anchor",
    "generate_selector",
]
