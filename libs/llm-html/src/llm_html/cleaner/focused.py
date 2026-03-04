"""Focused HTML cleaner with context preservation (Stage 2)."""
from __future__ import annotations

from typing import Optional, Set, List

from bs4 import BeautifulSoup, Tag

from .config import (
    CleaningConfig,
    FocusedCleaningConfig,
    FOCUSED_NOISE_TAGS,
    SELECTION_MARKER_ATTR,
    CONTEXT_RADIUS,
    MAX_PRESERVED_CHILDREN,
)
from .core import HTMLCleanerCore, CleaningResult, CleaningStats
from .scripts import ExtractedData, extract_all_data


class FocusedCleaner(HTMLCleanerCore):
    """Stage 2 cleaner with context-aware element preservation.

    Designed for selector extraction - preserves elements marked with
    `data-cmdop-id` and their surrounding context.

    Less aggressive than AggressiveCleaner to maintain page structure
    around important elements.
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """Initialize focused cleaner.

        Args:
            config: Cleaning configuration. Uses focused defaults if not provided.
        """
        config = config or FocusedCleaningConfig()
        # Ensure focused noise tags are used
        config.noise_tags = FOCUSED_NOISE_TAGS.copy()
        super().__init__(config)

    def clean(
        self,
        html: str,
        preserved_selectors: Optional[List[str]] = None,
    ) -> CleaningResult:
        """Perform focused HTML cleaning with element preservation.

        Args:
            html: Raw HTML string to clean.
            preserved_selectors: Additional CSS selectors for elements to preserve.

        Returns:
            CleaningResult with cleaned HTML and statistics.
        """
        stats = CleaningStats()
        stats.original_size = len(html)

        # Parse HTML
        soup = self.parse_html(html)

        # Extract valuable data before modifications
        extracted = extract_all_data(soup, html)

        # Mark elements to preserve
        preserved = self._mark_preserved_elements(soup, preserved_selectors)

        # Stage 1: Remove noise tags (respecting preserved)
        self.remove_noise_tags(soup, stats, preserved)

        # Stage 2: Remove noise by CSS selectors (respecting preserved)
        self.remove_noise_selectors(soup, stats, preserved)

        # Stage 3: Clean attributes (respecting preserved)
        if self.config.clean_attributes:
            self.clean_attributes(soup, stats, preserved)

        # Stage 4: Truncate long texts (respecting preserved)
        self.truncate_long_texts(soup, stats, preserved)

        # Stage 5: Remove comments
        if self.config.remove_comments:
            self.remove_comments(soup, stats)

        # Stage 6: Decode entities
        if self.config.decode_entities:
            self.decode_entities(soup)

        # Stage 7: Remove empty elements (respecting preserved)
        if self.config.remove_empty:
            self.remove_empty_elements(soup, stats, preserved)

        # Stage 8: Trim distant content (smart)
        self._trim_distant_content(soup, preserved, stats)

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

    def _mark_preserved_elements(
        self,
        soup: BeautifulSoup,
        selectors: Optional[List[str]] = None,
    ) -> Set[Tag]:
        """Mark elements that should be preserved during cleaning.

        Args:
            soup: BeautifulSoup object.
            selectors: Additional CSS selectors for preservation.

        Returns:
            Set of Tag objects that should not be modified.
        """
        preserved: Set[Tag] = set()

        # Find elements with plugin marker attribute
        for element in soup.find_all(attrs={SELECTION_MARKER_ATTR: True}):
            self._mark_with_context(element, preserved)

        # Find elements matching custom selectors
        if selectors:
            for selector in selectors:
                try:
                    for element in soup.select(selector):
                        self._mark_with_context(element, preserved)
                except Exception:
                    pass

        return preserved

    def _mark_with_context(
        self,
        element: Tag,
        preserved: Set[Tag],
        radius: int = CONTEXT_RADIUS,
    ) -> None:
        """Mark an element and its surrounding context for preservation.

        Args:
            element: BeautifulSoup Tag to mark.
            preserved: Set to add marked elements to.
            radius: Number of parent/sibling levels to preserve.
        """
        # Mark the element itself
        preserved.add(element)

        # Mark parent chain
        parent = element.parent
        for _ in range(radius):
            if parent is None or not hasattr(parent, "name"):
                break
            if parent.name == "[document]":
                break
            preserved.add(parent)
            parent = parent.parent

        # Mark children (limited)
        children = element.find_all(True) if hasattr(element, "find_all") else []
        for i, child in enumerate(children):
            if i >= MAX_PRESERVED_CHILDREN:
                break
            preserved.add(child)

        # Mark immediate siblings
        prev_sib = element.previous_sibling
        if prev_sib and hasattr(prev_sib, "name") and prev_sib.name:
            preserved.add(prev_sib)

        next_sib = element.next_sibling
        if next_sib and hasattr(next_sib, "name") and next_sib.name:
            preserved.add(next_sib)

    def _trim_distant_content(
        self,
        soup: BeautifulSoup,
        preserved: Set[Tag],
        stats: CleaningStats,
    ) -> None:
        """Remove top-level elements far from preserved content.

        Args:
            soup: BeautifulSoup object to modify.
            preserved: Set of preserved elements.
            stats: Statistics object to update.
        """
        if not preserved:
            return

        # Get body or root element
        body = soup.find("body") or soup

        # Get direct children of body
        children = [c for c in body.children if hasattr(c, "name") and c.name]
        if len(children) < 5:
            return

        # Find which children contain preserved elements
        has_preserved = []
        for i, child in enumerate(children):
            if child in preserved:
                has_preserved.append(i)
            elif any(p in preserved for p in child.find_all(True) if hasattr(child, "find_all")):
                has_preserved.append(i)

        if not has_preserved:
            return

        # Determine range to keep (first-2 to last+2)
        first_idx = min(has_preserved)
        last_idx = max(has_preserved)

        start_keep = max(0, first_idx - 2)
        end_keep = min(len(children), last_idx + 3)

        # Remove elements outside the range
        important_tags = {"nav", "header", "footer", "main", "form"}
        for i, child in enumerate(children):
            if i < start_keep or i >= end_keep:
                if child.name not in important_tags:
                    child.decompose()
                    stats.empty_removed += 1
