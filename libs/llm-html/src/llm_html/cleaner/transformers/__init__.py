"""HTML transformers for LLM-optimized processing."""
from .shadow_dom import (
    ShadowDOMFlattener,
    FlattenResult,
    FlattenStats,
    flatten_shadow_dom,
)
from .downsampler import (
    D2SnapDownsampler,
    D2SnapConfig,
    DownsampleResult,
    DownsampleStats,
    downsample_html,
    estimate_tokens,
    calculate_ui_feature_score,
)
from .chunker import (
    SemanticChunker,
    ChunkConfig,
    Chunk,
    ChunkResult,
    ItemPattern,
    chunk_html,
)

__all__ = [
    # Shadow DOM
    "ShadowDOMFlattener",
    "FlattenResult",
    "FlattenStats",
    "flatten_shadow_dom",
    # D2Snap Downsampler
    "D2SnapDownsampler",
    "D2SnapConfig",
    "DownsampleResult",
    "DownsampleStats",
    "downsample_html",
    "estimate_tokens",
    "calculate_ui_feature_score",
    # Semantic Chunker
    "SemanticChunker",
    "ChunkConfig",
    "Chunk",
    "ChunkResult",
    "ItemPattern",
    "chunk_html",
]
