"""Aggressive HTML cleaner for maximum compression (Stage 1)."""
from __future__ import annotations

from typing import Optional, Set

from bs4 import BeautifulSoup, Tag

from .config import CleaningConfig, AGGRESSIVE_NOISE_TAGS
from .core import HTMLCleanerCore, CleaningResult, CleaningStats
from .scripts import ExtractedData, extract_all_data


class AggressiveCleaner(HTMLCleanerCore):
    """Stage 1 cleaner for maximum HTML compression.

    Designed for page type detection - removes all non-essential content
    while preserving the basic page structure.

    Target: 80%+ size reduction.
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """Initialize aggressive cleaner.

        Args:
            config: Cleaning configuration. Uses aggressive defaults if not provided.
        """
        config = config or CleaningConfig()
        # Ensure aggressive noise tags are used
        config.noise_tags = AGGRESSIVE_NOISE_TAGS.copy()
        super().__init__(config)

    def clean(self, html: str) -> CleaningResult:
        """Perform aggressive HTML cleaning.

        Args:
            html: Raw HTML string to clean.

        Returns:
            CleaningResult with cleaned HTML and statistics.
        """
        stats = CleaningStats()
        stats.original_size = len(html)

        # Parse HTML
        soup = self.parse_html(html)

        # Extract valuable data before removing scripts
        extracted = extract_all_data(soup, html)

        # Stage 1: Remove noise tags (scripts, styles, etc.)
        self.remove_noise_tags(soup, stats)

        # Stage 2: Remove noise by CSS selectors
        self.remove_noise_selectors(soup, stats)

        # Stage 3: Clean attributes
        if self.config.clean_attributes:
            self.clean_attributes(soup, stats)

        # Stage 4: Truncate long texts
        self.truncate_long_texts(soup, stats)

        # Stage 5: Remove comments
        if self.config.remove_comments:
            self.remove_comments(soup, stats)

        # Stage 6: Decode entities
        if self.config.decode_entities:
            self.decode_entities(soup)

        # Stage 7: Iterative empty element removal
        if self.config.remove_empty:
            self.remove_empty_elements(soup, stats)

        # Stage 8: Remove duplicate blocks
        self._remove_duplicate_blocks(soup, stats)

        # Stage 9: Clean whitespace
        self.clean_whitespace(soup)

        # Get final HTML
        cleaned_html = str(soup)
        stats.cleaned_size = len(cleaned_html)

        return CleaningResult(
            html=cleaned_html,
            stats=stats,
            extracted_data=extracted,
        )

    def _remove_duplicate_blocks(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        threshold: int = 3,
        max_keep: int = 2,
    ) -> None:
        """Remove duplicate/repeating content blocks.

        When the same content structure appears multiple times (like
        product cards), keep only a few examples.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            threshold: Minimum duplicates to trigger removal.
            max_keep: Maximum number of duplicates to keep.
        """
        # Group elements by their structure signature
        signatures: dict[str, list[Tag]] = {}

        for tag_name in ["div", "li", "article", "section"]:
            for element in soup.find_all(tag_name):
                sig = self._get_structure_signature(element)
                if sig:
                    if sig not in signatures:
                        signatures[sig] = []
                    signatures[sig].append(element)

        # Remove duplicates exceeding threshold
        for sig, elements in signatures.items():
            if len(elements) >= threshold:
                # Keep first max_keep, remove rest
                for element in elements[max_keep:]:
                    element.decompose()
                    stats.empty_removed += 1

    def _get_structure_signature(self, element: Tag) -> str:
        """Get a signature representing element structure.

        Args:
            element: BeautifulSoup Tag object.

        Returns:
            Structure signature string, or empty if element is too simple.
        """
        if not hasattr(element, "find_all"):
            return ""

        # Get child tag names and classes
        children = element.find_all(True, recursive=False)
        if len(children) < 2:
            return ""

        parts = []
        for child in children[:5]:  # Limit to first 5 children
            tag = child.name
            classes = child.get("class", [])
            if isinstance(classes, list):
                class_str = ".".join(sorted(classes[:3]))
            else:
                class_str = str(classes)
            parts.append(f"{tag}:{class_str}")

        return "|".join(parts)
