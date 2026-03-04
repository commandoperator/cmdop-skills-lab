"""HTML Cleaner subpackage — aggressive & focused cleaning, SSR hydration, output formats."""

from __future__ import annotations

# Models
from .models import (
    OutputFormat,
    CleanerConfig,
    CleanerStats,
    ChunkInfo,
    CleanerResult,
)

# Main cleaner class
from .cleaner import (
    HTMLCleaner,
    clean,
    clean_to_json,
)

# Extractors
from .extractors import (
    HydrationExtractor,
    HydrationData,
    Framework,
    extract_hydration,
    detect_framework,
    ContextExtractor,
    ContextWindow,
    ContextConfig,
    extract_context,
    find_stable_anchor,
    generate_selector,
)

# Transformers
from .transformers import (
    ShadowDOMFlattener,
    flatten_shadow_dom,
    D2SnapDownsampler,
    D2SnapConfig,
    downsample_html,
    estimate_tokens,
    SemanticChunker,
    ChunkConfig,
    ChunkResult,
)

# Classifiers
from .classifiers import (
    ClassSemanticScorer,
    score_class,
    filter_classes,
    clean_classes,
    detect_css_framework,
)

# Output Formats
from .outputs import (
    AOMYAMLExporter,
    AOMConfig,
    to_aom_yaml,
    MarkdownExporter,
    MarkdownConfig,
    to_markdown,
    XTreeExporter,
    XTreeConfig,
    to_xtree,
)

# Pipeline
from .pipeline import (
    CleaningPipeline,
    PipelineConfig,
    PipelineResult,
    clean_html,
    clean_for_llm,
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
]
