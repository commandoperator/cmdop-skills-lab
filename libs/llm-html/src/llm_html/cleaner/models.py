"""Pydantic models for HTML Cleaner.

All public API types are defined here using Pydantic 2 for:
- Validation of input configuration
- Serialization of output results
- Clear API contracts
"""
from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, computed_field


class OutputFormat(str, Enum):
    """Supported output formats."""
    HTML = "html"
    MARKDOWN = "markdown"
    AOM = "aom"
    XTREE = "xtree"


class CleanerConfig(BaseModel):
    """Configuration for HTML cleaning.

    Example:
        config = CleanerConfig(
            max_tokens=5000,
            output_format=OutputFormat.MARKDOWN,
            filter_classes=True,
        )
    """

    # Token budget
    max_tokens: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Target maximum tokens in output",
    )

    # Output format
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML,
        description="Output format: html, markdown, aom, xtree",
    )

    # Cleaning options
    remove_scripts: bool = Field(
        default=True,
        description="Remove script tags",
    )
    remove_styles: bool = Field(
        default=True,
        description="Remove style tags and inline styles",
    )
    remove_comments: bool = Field(
        default=True,
        description="Remove HTML comments",
    )
    remove_hidden: bool = Field(
        default=True,
        description="Remove hidden elements",
    )
    remove_empty: bool = Field(
        default=True,
        description="Remove empty container elements",
    )

    # Class handling
    filter_classes: bool = Field(
        default=True,
        description="Filter CSS classes by semantic score",
    )
    class_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum score to keep a class (0.0-1.0)",
    )

    # Chunking
    enable_chunking: bool = Field(
        default=True,
        description="Enable semantic chunking for large content",
    )
    chunk_max_items: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum items per chunk",
    )

    # Preservation
    preserve_selectors: List[str] = Field(
        default_factory=list,
        description="CSS selectors for elements to always preserve",
    )

    # Try hydration extraction first (most efficient for SSR sites)
    try_hydration: bool = Field(
        default=True,
        description="Try to extract SSR hydration data before DOM cleaning",
    )

    model_config = {
        "use_enum_values": True,
        "json_schema_extra": {
            "examples": [
                {
                    "max_tokens": 5000,
                    "output_format": "markdown",
                    "filter_classes": True,
                    "class_threshold": 0.3,
                }
            ]
        }
    }


class CleanerStats(BaseModel):
    """Statistics about the cleaning process.

    Provides detailed metrics for comparing before/after.
    """

    # Size metrics
    original_size: int = Field(
        default=0,
        ge=0,
        description="Original HTML size in bytes",
    )
    cleaned_size: int = Field(
        default=0,
        ge=0,
        description="Cleaned HTML size in bytes",
    )

    # Token estimates
    original_tokens: int = Field(
        default=0,
        ge=0,
        description="Estimated tokens before cleaning (~4 chars/token)",
    )
    cleaned_tokens: int = Field(
        default=0,
        ge=0,
        description="Estimated tokens after cleaning",
    )

    # Removal counts
    scripts_removed: int = Field(default=0, ge=0)
    styles_removed: int = Field(default=0, ge=0)
    comments_removed: int = Field(default=0, ge=0)
    hidden_removed: int = Field(default=0, ge=0)
    empty_removed: int = Field(default=0, ge=0)
    elements_removed: int = Field(default=0, ge=0)

    # Class filtering
    classes_total: int = Field(default=0, ge=0)
    classes_removed: int = Field(default=0, ge=0)
    classes_kept: int = Field(default=0, ge=0)

    # Processing info
    processing_time_ms: float = Field(
        default=0.0,
        ge=0,
        description="Processing time in milliseconds",
    )

    @computed_field
    @property
    def reduction_percent(self) -> float:
        """Calculate size reduction percentage."""
        if self.original_size == 0:
            return 0.0
        return round((1 - self.cleaned_size / self.original_size) * 100, 2)

    @computed_field
    @property
    def token_reduction_percent(self) -> float:
        """Calculate token reduction percentage."""
        if self.original_tokens == 0:
            return 0.0
        return round((1 - self.cleaned_tokens / self.original_tokens) * 100, 2)

    @computed_field
    @property
    def compression_ratio(self) -> float:
        """Compression ratio (original/cleaned)."""
        if self.cleaned_size == 0:
            return 0.0
        return round(self.original_size / self.cleaned_size, 2)


class ChunkInfo(BaseModel):
    """Information about a single chunk."""

    index: int = Field(description="Chunk index (0-based)")
    html: str = Field(description="Chunk HTML content")
    tokens: int = Field(default=0, description="Estimated tokens")
    items: int = Field(default=0, description="Number of items in chunk")


class CleanerResult(BaseModel):
    """Result of HTML cleaning operation.

    Contains cleaned content, statistics, and any extracted data.

    Example:
        result = cleaner.clean(html)
        print(f"Reduced by {result.stats.reduction_percent}%")
        print(f"Tokens: {result.stats.original_tokens} → {result.stats.cleaned_tokens}")

        if result.hydration_data:
            # Use SSR data directly (most efficient)
            products = result.hydration_data.get("products", [])
        else:
            # Use cleaned HTML
            process_html(result.html)
    """

    # Main output
    html: str = Field(
        default="",
        description="Cleaned HTML content",
    )
    output: str = Field(
        default="",
        description="Content in requested output format",
    )

    # Statistics
    stats: CleanerStats = Field(
        default_factory=CleanerStats,
        description="Detailed cleaning statistics",
    )

    # Extracted data
    hydration_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="SSR hydration data if extracted (Next.js, Nuxt, etc.)",
    )
    structured_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSON-LD structured data if found",
    )

    # Chunking results
    was_chunked: bool = Field(
        default=False,
        description="Whether content was split into chunks",
    )
    chunks: List[ChunkInfo] = Field(
        default_factory=list,
        description="List of chunks if chunking was applied",
    )
    total_chunks: int = Field(
        default=0,
        ge=0,
        description="Total number of chunks",
    )

    # Metadata
    extraction_method: Optional[str] = Field(
        default=None,
        description="How data was extracted: 'hydration', 'dom', 'hybrid'",
    )
    framework_detected: Optional[str] = Field(
        default=None,
        description="Detected SSR framework if any",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.HTML,
        description="Output format used",
    )

    @computed_field
    @property
    def success(self) -> bool:
        """Whether cleaning was successful."""
        return bool(self.html or self.hydration_data)

    @computed_field
    @property
    def has_hydration(self) -> bool:
        """Whether SSR hydration data was extracted."""
        return self.hydration_data is not None

    model_config = {
        "use_enum_values": True,
    }


# =============================================================================
# Lightweight internal types (keep as dataclass for performance)
# =============================================================================
# ItemPattern, Chunk internal structures stay as dataclasses in their modules
# Only public API types are Pydantic models
