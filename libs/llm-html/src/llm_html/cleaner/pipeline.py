"""Universal Cleaning Pipeline for LLM-optimized HTML processing.

Provides a configurable pipeline that automatically applies
optimal cleaning steps based on content analysis.

Key features:
- Hydration-first: Extract SSR data before DOM parsing
- Adaptive cleaning: Apply transformations based on content
- Token budget: Target specific token limits
- Multiple output formats: HTML, Markdown, AOM YAML, XTree
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union
from bs4 import BeautifulSoup, Tag


@dataclass
class PipelineConfig:
    """Configuration for the cleaning pipeline."""

    # Token budget
    max_tokens: int = 10000
    """Target maximum tokens in output."""

    # Cleaning options
    remove_scripts: bool = True
    """Remove script tags."""

    remove_styles: bool = True
    """Remove style tags and inline styles."""

    remove_comments: bool = True
    """Remove HTML comments."""

    remove_hidden: bool = True
    """Remove hidden elements."""

    remove_empty: bool = True
    """Remove empty container elements."""

    # Class handling
    filter_classes: bool = True
    """Filter CSS classes by semantic score."""

    class_threshold: float = 0.3
    """Minimum score to keep a class."""

    # Chunking
    enable_chunking: bool = True
    """Enable semantic chunking for large content."""

    chunk_max_items: int = 20
    """Maximum items per chunk."""

    # Output
    output_format: str = "html"
    """Output format: 'html', 'markdown', 'aom', 'xtree'."""

    preserve_selectors: List[str] = field(default_factory=list)
    """CSS selectors for elements to always preserve."""


@dataclass
class PipelineResult:
    """Result from the cleaning pipeline."""

    # Main output
    output: str
    """Cleaned content in requested format."""

    html: str = ""
    """Cleaned HTML (always available)."""

    # Token stats
    original_tokens: int = 0
    """Original content token estimate."""

    cleaned_tokens: int = 0
    """Cleaned content token estimate."""

    reduction_percent: float = 0.0
    """Token reduction percentage."""

    # Extracted data
    hydration_data: Optional[dict[str, Any]] = None
    """SSR hydration data if extracted."""

    structured_data: Optional[dict[str, Any]] = None
    """JSON-LD structured data if found."""

    # Chunking
    was_chunked: bool = False
    """Whether content was split into chunks."""

    chunks: List[str] = field(default_factory=list)
    """List of chunks if chunked."""

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional processing metadata."""


class CleaningPipeline:
    """Universal HTML cleaning pipeline.

    Automatically applies optimal cleaning based on content analysis:
    1. Try hydration extraction (most efficient for SSR sites)
    2. Apply aggressive DOM cleaning
    3. Filter CSS classes
    4. Chunk if over token budget
    5. Convert to requested output format

    Example:
        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        # Check for SSR data first (most efficient)
        if result.hydration_data:
            products = result.hydration_data.get('products', [])
        else:
            # Use cleaned output
            print(result.output)

    With custom config:
        config = PipelineConfig(
            max_tokens=5000,
            output_format='markdown',
            enable_chunking=True,
        )
        result = pipeline.process(html, config)
    """

    def __init__(self, config: PipelineConfig | None = None):
        """Initialize pipeline.

        Args:
            config: Optional default configuration.
        """
        self.default_config = config if config is not None else PipelineConfig()

    def process(
        self,
        html: str,
        config: PipelineConfig | None = None,
    ) -> PipelineResult:
        """Process HTML through the cleaning pipeline.

        Args:
            html: Raw HTML string.
            config: Optional configuration override.

        Returns:
            PipelineResult with cleaned content.
        """
        config = config if config is not None else self.default_config

        original_tokens = self._estimate_tokens(html)
        metadata: dict[str, Any] = {}

        # Step 1: Try hydration extraction (CRITICAL - most efficient path)
        hydration_data = self._try_hydration_extraction(html)

        if hydration_data:
            # Success! Return JSON data directly
            output = json.dumps(hydration_data, ensure_ascii=False, indent=2)
            return PipelineResult(
                output=output,
                html="",
                original_tokens=original_tokens,
                cleaned_tokens=self._estimate_tokens(output),
                reduction_percent=self._calc_reduction(original_tokens, len(output) // 4),
                hydration_data=hydration_data,
                metadata={'extraction_method': 'hydration'},
            )

        # Step 2: Extract structured data (JSON-LD)
        structured_data = self._extract_structured_data(html)

        # Step 3: Parse and clean DOM
        soup = BeautifulSoup(html, 'lxml')
        soup = self._clean_dom(soup, config)

        # Step 4: Filter CSS classes
        if config.filter_classes:
            self._filter_classes(soup, config.class_threshold)

        # Step 5: Check token budget and chunk if needed
        cleaned_html = str(soup)
        cleaned_tokens = self._estimate_tokens(cleaned_html)
        chunks: List[str] = []
        was_chunked = False

        if config.enable_chunking and cleaned_tokens > config.max_tokens:
            chunks = self._chunk_content(soup, config)
            if len(chunks) > 1:
                was_chunked = True
                cleaned_html = chunks[0]  # Use first chunk as main output
                metadata['total_chunks'] = len(chunks)

        # Step 6: Convert to output format
        output = self._format_output(cleaned_html, config.output_format)

        return PipelineResult(
            output=output,
            html=cleaned_html,
            original_tokens=original_tokens,
            cleaned_tokens=cleaned_tokens,
            reduction_percent=self._calc_reduction(original_tokens, cleaned_tokens),
            hydration_data=None,
            structured_data=structured_data,
            was_chunked=was_chunked,
            chunks=chunks,
            metadata=metadata,
        )

    def _try_hydration_extraction(self, html: str) -> Optional[dict[str, Any]]:
        """Try to extract SSR hydration data.

        Args:
            html: Raw HTML string.

        Returns:
            Extracted data or None.
        """
        from .extractors import extract_hydration

        hydration = extract_hydration(html)
        if hydration.has_data:
            return hydration.page_props
        return None

    def _extract_structured_data(self, html: str) -> Optional[dict[str, Any]]:
        """Extract JSON-LD structured data.

        Args:
            html: Raw HTML string.

        Returns:
            Structured data or None.
        """
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        if not matches:
            return None

        items = []
        for match in matches:
            try:
                data = json.loads(match.strip())
                items.append(data)
            except json.JSONDecodeError:
                continue

        if not items:
            return None

        if len(items) == 1:
            return items[0] if isinstance(items[0], dict) else {'items': items[0]}
        return {'items': items}

    def _clean_dom(self, soup: BeautifulSoup, config: PipelineConfig) -> BeautifulSoup:
        """Apply DOM cleaning.

        Args:
            soup: BeautifulSoup document.
            config: Configuration.

        Returns:
            Cleaned soup.
        """
        from .aggressive import AggressiveCleaner

        cleaner = AggressiveCleaner()
        # AggressiveCleaner expects HTML string
        result = cleaner.clean(str(soup))
        return BeautifulSoup(result.html, 'lxml')

    def _filter_classes(self, soup: BeautifulSoup, threshold: float) -> None:
        """Filter CSS classes by semantic score.

        Args:
            soup: BeautifulSoup document (modified in place).
            threshold: Minimum score to keep.
        """
        from .classifiers import filter_classes

        for element in soup.find_all(True):
            if element.has_attr('class'):
                classes = element.get('class')
                if classes and isinstance(classes, list):
                    filtered = filter_classes(classes, threshold=threshold)
                    if filtered:
                        element['class'] = filtered
                    else:
                        del element['class']

    def _chunk_content(self, soup: BeautifulSoup, config: PipelineConfig) -> List[str]:
        """Chunk content if over token budget.

        Args:
            soup: BeautifulSoup document.
            config: Configuration.

        Returns:
            List of HTML chunks.
        """
        from .transformers import SemanticChunker, ChunkConfig

        chunk_config = ChunkConfig(
            max_tokens=config.max_tokens,
            max_items=config.chunk_max_items,
            preserve_context=True,
        )

        chunker = SemanticChunker(chunk_config)
        result = chunker.chunk(soup)

        return [chunk.html for chunk in result.chunks]

    def _format_output(self, html: str, format_type: str) -> str:
        """Convert HTML to requested output format.

        Args:
            html: Cleaned HTML string.
            format_type: Output format.

        Returns:
            Formatted output string.
        """
        if format_type == "html":
            return html

        soup = BeautifulSoup(html, 'lxml')

        if format_type == "markdown":
            from .outputs import MarkdownExporter
            return MarkdownExporter().export(soup)
        elif format_type == "aom":
            from .outputs import AOMYAMLExporter
            return AOMYAMLExporter().export(soup)
        elif format_type == "xtree":
            from .outputs import XTreeExporter
            return XTreeExporter().export(soup)

        return html

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count.

        Args:
            text: Text to estimate.

        Returns:
            Estimated token count.
        """
        return len(text) // 4

    def _calc_reduction(self, original: int, cleaned: int) -> float:
        """Calculate reduction percentage.

        Args:
            original: Original token count.
            cleaned: Cleaned token count.

        Returns:
            Reduction percentage.
        """
        if original == 0:
            return 0.0
        return (1 - cleaned / original) * 100


# =============================================================================
# Convenience Functions
# =============================================================================

def clean_html(
    html: str,
    max_tokens: int = 10000,
    output_format: str = "html",
    enable_chunking: bool = True,
) -> PipelineResult:
    """Clean HTML with universal pipeline (convenience function).

    Args:
        html: Raw HTML string.
        max_tokens: Target maximum tokens.
        output_format: Output format.
        enable_chunking: Enable chunking.

    Returns:
        PipelineResult with cleaned content.
    """
    config = PipelineConfig(
        max_tokens=max_tokens,
        output_format=output_format,
        enable_chunking=enable_chunking,
    )
    return CleaningPipeline(config).process(html)


def clean_for_llm(
    html: str,
    max_tokens: int = 10000,
) -> Union[str, dict[str, Any]]:
    """Clean HTML for LLM, returning JSON if SSR data available.

    This is the recommended entry point for LLM processing.
    Returns JSON dict if hydration data extracted, otherwise
    returns cleaned HTML string.

    Args:
        html: Raw HTML string.
        max_tokens: Target maximum tokens.

    Returns:
        Dict (if SSR data found) or cleaned HTML string.
    """
    config = PipelineConfig(max_tokens=max_tokens)
    result = CleaningPipeline(config).process(html)

    if result.hydration_data:
        return result.hydration_data

    return result.output
