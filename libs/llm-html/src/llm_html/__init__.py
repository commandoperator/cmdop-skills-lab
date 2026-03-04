"""HTML Cleaner module for LLM-optimized HTML processing.

Provides intelligent HTML cleaning optimized for Large Language Models:

- **Hydration-First**: Extract SSR data (Next.js, Nuxt, etc.) before DOM parsing
- **Token Budget**: Target specific token limits with adaptive downsampling
- **Multiple Outputs**: HTML, Markdown, AOM YAML, XTree formats
- **Detailed Statistics**: Track reduction, timing, element counts

Example usage:
    from llm_html import HTMLCleaner, CleanerConfig, OutputFormat

    # Basic usage
    cleaner = HTMLCleaner()
    result = cleaner.clean(html)

    # Check statistics
    print(f"Size: {result.stats.original_size} → {result.stats.cleaned_size}")
    print(f"Reduction: {result.stats.reduction_percent}%")
    print(f"Scripts removed: {result.stats.scripts_removed}")

    # Use hydration data if available (most efficient)
    if result.hydration_data:
        products = result.hydration_data.get("products", [])
    else:
        cleaned = result.html

    # Custom configuration
    config = CleanerConfig(
        max_tokens=5000,
        output_format=OutputFormat.MARKDOWN,
        filter_classes=True,
    )
    cleaner = HTMLCleaner(config)
    result = cleaner.clean(html)

Convenience functions:
    from llm_html import clean, clean_to_json

    # Quick clean with default settings
    result = clean(html)

    # Get JSON if SSR data available, otherwise cleaned HTML
    data = clean_to_json(html)
"""
from __future__ import annotations

from typing import Any, Dict, Union

# =============================================================================
# Cleaner subpackage (HTML cleaning pipeline)
# =============================================================================

# Models
from .cleaner.models import (
    OutputFormat,
    CleanerConfig,
    CleanerStats,
    ChunkInfo,
    CleanerResult,
)

# Main cleaner class
from .cleaner.cleaner import (
    HTMLCleaner,
    clean,
    clean_to_json,
)

# Extractors
from .cleaner.extractors import (
    # Hydration extraction
    HydrationExtractor,
    HydrationData,
    Framework,
    extract_hydration,
    detect_framework,
    # Context Window
    ContextExtractor,
    ContextWindow,
    ContextConfig,
    extract_context,
    find_stable_anchor,
    generate_selector,
)

# Transformers
from .cleaner.transformers import (
    # Shadow DOM
    ShadowDOMFlattener,
    flatten_shadow_dom,
    # D2Snap Downsampling
    D2SnapDownsampler,
    D2SnapConfig,
    downsample_html,
    estimate_tokens,
    # Semantic Chunking
    SemanticChunker,
    ChunkConfig,
    ChunkResult,
)

# Classifiers
from .cleaner.classifiers import (
    ClassSemanticScorer,
    score_class,
    filter_classes,
    clean_classes,
    detect_css_framework,
)

# Output Formats
from .cleaner.outputs import (
    # AOM YAML (Playwright-style Aria Snapshot)
    AOMYAMLExporter,
    AOMConfig,
    to_aom_yaml,
    # Markdown
    MarkdownExporter,
    MarkdownConfig,
    to_markdown,
    # XTree
    XTreeExporter,
    XTreeConfig,
    to_xtree,
)

# Pipeline
from .cleaner.pipeline import (
    CleaningPipeline,
    PipelineConfig,
    PipelineResult,
    clean_html,
    clean_for_llm,
)

# =============================================================================
# Helpers (parsing utilities)
# =============================================================================

from .helpers import (
    json_to_toon,
    JsonCleaner,
    html_to_text,
    extract_links,
    extract_images,
)


__all__ = [
    # Primary API
    "HTMLCleaner",
    "CleanerConfig",
    "CleanerResult",
    "CleanerStats",
    "ChunkInfo",
    "OutputFormat",
    "clean",
    "clean_to_json",
    # Extractors - Hydration
    "HydrationExtractor",
    "HydrationData",
    "Framework",
    "extract_hydration",
    "detect_framework",
    # Extractors - Context Window
    "ContextExtractor",
    "ContextWindow",
    "ContextConfig",
    "extract_context",
    "find_stable_anchor",
    "generate_selector",
    # Transformers - Shadow DOM
    "ShadowDOMFlattener",
    "flatten_shadow_dom",
    # Transformers - D2Snap
    "D2SnapDownsampler",
    "D2SnapConfig",
    "downsample_html",
    "estimate_tokens",
    # Transformers - Chunking
    "SemanticChunker",
    "ChunkConfig",
    "ChunkResult",
    # Classifiers
    "ClassSemanticScorer",
    "score_class",
    "filter_classes",
    "clean_classes",
    "detect_css_framework",
    # Outputs
    "AOMYAMLExporter",
    "AOMConfig",
    "to_aom_yaml",
    "MarkdownExporter",
    "MarkdownConfig",
    "to_markdown",
    "XTreeExporter",
    "XTreeConfig",
    "to_xtree",
    # Pipeline
    "CleaningPipeline",
    "PipelineConfig",
    "PipelineResult",
    "clean_html",
    "clean_for_llm",
    # Helpers
    "json_to_toon",
    "JsonCleaner",
    "html_to_text",
    "extract_links",
    "extract_images",
]
