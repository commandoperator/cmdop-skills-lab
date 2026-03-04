"""Main HTMLCleaner class with Pydantic 2 models.

This is the primary entry point for HTML cleaning with full
statistics and extracted data.
"""
from __future__ import annotations

import time
from typing import Union

from bs4 import BeautifulSoup, Comment, Tag

from .models import (
    CleanerConfig,
    CleanerResult,
    CleanerStats,
    ChunkInfo,
    OutputFormat,
)


class HTMLCleaner:
    """Main HTML Cleaner with detailed statistics.

    Cleans HTML for LLM processing with multiple strategies:
    1. Hydration extraction (SSR sites) - most efficient
    2. DOM cleaning with class filtering
    3. Semantic chunking for large content
    4. Multiple output formats

    Example:
        cleaner = HTMLCleaner()
        result = cleaner.clean(html)

        # Check statistics
        print(f"Size: {result.stats.original_size} → {result.stats.cleaned_size}")
        print(f"Reduction: {result.stats.reduction_percent}%")
        print(f"Tokens: {result.stats.original_tokens} → {result.stats.cleaned_tokens}")

        # Use result
        if result.hydration_data:
            data = result.hydration_data
        else:
            cleaned = result.html

    With configuration:
        config = CleanerConfig(
            max_tokens=5000,
            output_format=OutputFormat.MARKDOWN,
            filter_classes=True,
        )
        cleaner = HTMLCleaner(config)
        result = cleaner.clean(html)
    """

    def __init__(self, config: CleanerConfig | None = None):
        """Initialize cleaner with optional configuration.

        Args:
            config: Cleaning configuration. Uses defaults if not provided.
        """
        self.config = config or CleanerConfig()

    def clean(
        self,
        html: str,
        config: CleanerConfig | None = None,
    ) -> CleanerResult:
        """Clean HTML and return result with detailed statistics.

        Args:
            html: Raw HTML string to clean.
            config: Optional config override for this call.

        Returns:
            CleanerResult with cleaned content and statistics.
        """
        start_time = time.perf_counter()
        cfg = config if config is not None else self.config

        # Initialize stats
        stats = CleanerStats(
            original_size=len(html),
            original_tokens=self._estimate_tokens(html),
        )

        # Step 1: Try hydration extraction first (most efficient)
        if cfg.try_hydration:
            hydration_result = self._try_hydration(html, cfg, stats, start_time)
            if hydration_result:
                return hydration_result

        # Step 2: Parse HTML
        soup = BeautifulSoup(html, 'lxml')

        # Step 3: Clean DOM with stats tracking
        soup, stats = self._clean_dom(soup, cfg, stats)

        # Step 4: Filter classes
        if cfg.filter_classes:
            soup, stats = self._filter_classes(soup, cfg.class_threshold, stats)

        # Step 5: Get cleaned HTML
        cleaned_html = str(soup)
        stats.cleaned_size = len(cleaned_html)
        stats.cleaned_tokens = self._estimate_tokens(cleaned_html)

        # Step 6: Check chunking
        chunks: list[ChunkInfo] = []
        was_chunked = False

        if cfg.enable_chunking and stats.cleaned_tokens > cfg.max_tokens:
            chunks, was_chunked = self._chunk_content(soup, cfg)

        # Step 7: Convert to output format
        # Always format from full cleaned HTML, chunks are available separately
        output = self._format_output(cleaned_html, cfg.output_format)

        # Step 8: Extract structured data
        structured_data = self._extract_structured_data(html)

        # Finalize stats
        stats.processing_time_ms = (time.perf_counter() - start_time) * 1000

        return CleanerResult(
            html=cleaned_html,
            output=output,
            stats=stats,
            hydration_data=None,
            structured_data=structured_data,
            was_chunked=was_chunked,
            chunks=chunks,
            total_chunks=len(chunks),
            extraction_method="dom",
            output_format=cfg.output_format,
        )

    def _try_hydration(
        self,
        html: str,
        config: CleanerConfig,
        stats: CleanerStats,
        start_time: float,
    ) -> CleanerResult | None:
        """Try to extract SSR hydration data.

        Returns CleanerResult if successful, None otherwise.
        """
        from .extractors import extract_hydration

        hydration = extract_hydration(html)

        if not hydration.has_data:
            return None

        # Success! Return JSON data
        import json
        output = json.dumps(hydration.page_props, ensure_ascii=False, indent=2)

        stats.cleaned_size = len(output)
        stats.cleaned_tokens = self._estimate_tokens(output)
        stats.processing_time_ms = (time.perf_counter() - start_time) * 1000

        return CleanerResult(
            html="",
            output=output,
            stats=stats,
            hydration_data=hydration.page_props,
            structured_data=None,
            was_chunked=False,
            chunks=[],
            total_chunks=0,
            extraction_method="hydration",
            framework_detected=hydration.framework.value if hydration.framework else None,
            output_format=config.output_format,
        )

    def _clean_dom(
        self,
        soup: BeautifulSoup,
        config: CleanerConfig,
        stats: CleanerStats,
    ) -> tuple[BeautifulSoup, CleanerStats]:
        """Clean DOM and track statistics."""

        # Remove scripts
        if config.remove_scripts:
            scripts = soup.find_all('script')
            stats.scripts_removed = len(scripts)
            stats.elements_removed += len(scripts)
            for script in scripts:
                script.decompose()

        # Remove styles
        if config.remove_styles:
            styles = soup.find_all('style')
            stats.styles_removed = len(styles)
            stats.elements_removed += len(styles)
            for style in styles:
                style.decompose()

            # Remove inline styles
            for element in soup.find_all(style=True):
                if isinstance(element, Tag):
                    del element['style']

        # Remove comments
        if config.remove_comments:
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            stats.comments_removed = len(comments)
            for comment in comments:
                comment.extract()

        # Remove hidden elements
        if config.remove_hidden:
            hidden_selectors = [
                '[hidden]',
                '[aria-hidden="true"]',
                '[style*="display:none"]',
                '[style*="display: none"]',
                '[style*="visibility:hidden"]',
            ]
            hidden_count = 0
            for selector in hidden_selectors:
                try:
                    elements = soup.select(selector)
                    hidden_count += len(elements)
                    for el in elements:
                        el.decompose()
                except Exception:
                    pass
            stats.hidden_removed = hidden_count
            stats.elements_removed += hidden_count

        # Remove common non-content elements
        non_content_tags = [
            'noscript', 'iframe', 'svg', 'canvas',
            'video', 'audio', 'map', 'object', 'embed',
        ]
        for tag in non_content_tags:
            elements = soup.find_all(tag)
            stats.elements_removed += len(elements)
            for el in elements:
                el.decompose()

        # Remove empty elements
        if config.remove_empty:
            empty_count = self._remove_empty_elements(soup)
            stats.empty_removed = empty_count
            stats.elements_removed += empty_count

        return soup, stats

    def _remove_empty_elements(self, soup: BeautifulSoup) -> int:
        """Remove empty container elements."""
        empty_containers = ['div', 'span', 'p', 'section', 'article']
        removed = 0

        changed = True
        while changed:
            changed = False
            for tag_name in empty_containers:
                for element in soup.find_all(tag_name):
                    if not isinstance(element, Tag):
                        continue
                    if not element.get_text(strip=True) and not element.find_all(True):
                        element.decompose()
                        removed += 1
                        changed = True

        return removed

    def _filter_classes(
        self,
        soup: BeautifulSoup,
        threshold: float,
        stats: CleanerStats,
    ) -> tuple[BeautifulSoup, CleanerStats]:
        """Filter CSS classes by semantic score."""
        from .classifiers import filter_classes

        total_classes = 0
        removed_classes = 0

        for element in soup.find_all(True):
            if not isinstance(element, Tag):
                continue
            if element.has_attr('class'):
                classes = element.get('class')
                if classes and isinstance(classes, list):
                    total_classes += len(classes)
                    filtered = filter_classes(classes, threshold=threshold)
                    removed_classes += len(classes) - len(filtered)

                    if filtered:
                        element['class'] = filtered
                    else:
                        del element['class']

        stats.classes_total = total_classes
        stats.classes_removed = removed_classes
        stats.classes_kept = total_classes - removed_classes

        return soup, stats

    def _chunk_content(
        self,
        soup: BeautifulSoup,
        config: CleanerConfig,
    ) -> tuple[list[ChunkInfo], bool]:
        """Chunk content if over token budget."""
        from .transformers import SemanticChunker, ChunkConfig

        chunk_config = ChunkConfig(
            max_tokens=config.max_tokens,
            max_items=config.chunk_max_items,
            preserve_context=True,
        )

        chunker = SemanticChunker(chunk_config)
        result = chunker.chunk(soup)

        if not result.was_chunked:
            return [], False

        chunks = [
            ChunkInfo(
                index=i,
                html=chunk.html,
                tokens=chunk.estimated_tokens,
                items=chunk.item_count,
            )
            for i, chunk in enumerate(result.chunks)
        ]

        return chunks, True

    def _format_output(self, html: str, format_type: OutputFormat) -> str:
        """Convert HTML to requested output format."""
        if format_type == OutputFormat.HTML:
            return html

        soup = BeautifulSoup(html, 'lxml')

        if format_type == OutputFormat.MARKDOWN:
            from .outputs import MarkdownExporter
            return MarkdownExporter().export(soup)
        elif format_type == OutputFormat.AOM:
            from .outputs import AOMYAMLExporter
            return AOMYAMLExporter().export(soup)
        elif format_type == OutputFormat.XTREE:
            from .outputs import XTreeExporter
            return XTreeExporter().export(soup)

        return html

    def _extract_structured_data(self, html: str) -> dict | None:
        """Extract JSON-LD structured data."""
        import json
        import re

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

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (~4 chars per token)."""
        return len(text) // 4


# =============================================================================
# Convenience Functions
# =============================================================================

def clean(
    html: str,
    max_tokens: int = 10000,
    output_format: str = "html",
    filter_classes: bool = True,
) -> CleanerResult:
    """Clean HTML with default settings.

    Args:
        html: Raw HTML string.
        max_tokens: Target maximum tokens.
        output_format: Output format (html, markdown, aom, xtree).
        filter_classes: Filter CSS classes by semantic score.

    Returns:
        CleanerResult with cleaned content and statistics.
    """
    config = CleanerConfig(
        max_tokens=max_tokens,
        output_format=OutputFormat(output_format),
        filter_classes=filter_classes,
    )
    return HTMLCleaner(config).clean(html)


def clean_to_json(html: str) -> Union[dict, str]:
    """Clean HTML, preferring JSON output if SSR data available.

    Most efficient for SSR sites (Next.js, Nuxt, etc.).

    Args:
        html: Raw HTML string.

    Returns:
        Dict if SSR data extracted, cleaned HTML string otherwise.
    """
    result = HTMLCleaner().clean(html)

    if result.hydration_data:
        return result.hydration_data

    return result.html
