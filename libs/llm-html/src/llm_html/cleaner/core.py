"""Core HTML cleaner with shared functionality."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Set, Optional

from bs4 import BeautifulSoup, Comment, Tag

from .config import (
    CleaningConfig,
    REMOVE_ATTRIBUTES,
    KEEP_ATTRIBUTES,
    KEEP_ATTRIBUTE_PREFIXES,
    VOID_ELEMENTS,
    EMPTY_REMOVAL_TAGS,
    HASH_CLASS_PATTERNS,
    SEMANTIC_CLASS_PATTERNS,
    UTILITY_CLASS_PATTERNS,
    TRACKING_URL_PATTERNS,
    PROTECTED_ENTITIES,
    COMMON_ENTITIES,
    MAX_HTML_SIZE,
    SELECTION_MARKER_ATTR,
)
from .scripts import ExtractedData, is_json_script, extract_all_data


@dataclass
class CleaningStats:
    """Statistics from HTML cleaning operation."""

    original_size: int = 0
    cleaned_size: int = 0
    scripts_removed: int = 0
    styles_removed: int = 0
    json_preserved: int = 0
    empty_removed: int = 0
    attrs_cleaned: int = 0
    texts_truncated: int = 0
    base64_removed: int = 0
    tracking_removed: int = 0
    comments_removed: int = 0


@dataclass
class CleaningResult:
    """Result of HTML cleaning operation."""

    html: str
    stats: CleaningStats = field(default_factory=CleaningStats)
    extracted_data: ExtractedData = field(default_factory=ExtractedData)


class HTMLCleanerCore:
    """Base HTML cleaner with shared functionality.

    This class provides the core cleaning methods used by both
    AggressiveCleaner and FocusedCleaner.
    """

    def __init__(self, config: Optional[CleaningConfig] = None):
        """Initialize cleaner with configuration.

        Args:
            config: Cleaning configuration. Uses defaults if not provided.
        """
        self.config = config or CleaningConfig()

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML string into BeautifulSoup object.

        Args:
            html: Raw HTML string.

        Returns:
            BeautifulSoup object.

        Raises:
            ValueError: If HTML exceeds maximum size.
        """
        if len(html) > self.config.max_html_size:
            html = html[:self.config.max_html_size]

        return BeautifulSoup(html, "lxml")

    def remove_noise_tags(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        preserved: Optional[Set[Tag]] = None,
    ) -> None:
        """Remove noise tags from the document.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            preserved: Set of elements to preserve.
        """
        preserved = preserved or set()

        for tag_name in self.config.noise_tags:
            for element in soup.find_all(tag_name):
                if element in preserved:
                    continue

                # Special handling for scripts
                if tag_name == "script":
                    if is_json_script(element):
                        stats.json_preserved += 1
                        continue
                    stats.scripts_removed += 1
                elif tag_name == "style":
                    stats.styles_removed += 1

                element.decompose()

    def remove_noise_selectors(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        preserved: Optional[Set[Tag]] = None,
    ) -> None:
        """Remove elements matching noise selectors.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            preserved: Set of elements to preserve.
        """
        preserved = preserved or set()

        for selector in self.config.noise_selectors:
            try:
                for element in soup.select(selector):
                    if element in preserved:
                        continue
                    element.decompose()
            except Exception:
                # Invalid selector, skip
                pass

    def clean_attributes(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        preserved: Optional[Set[Tag]] = None,
    ) -> None:
        """Clean attributes from all elements.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            preserved: Set of elements to preserve.
        """
        preserved = preserved or set()

        for element in soup.find_all(True):
            if element in preserved:
                continue

            self._clean_element_attributes(element, stats)

    def _clean_element_attributes(self, element: Tag, stats: CleaningStats) -> None:
        """Clean attributes from a single element.

        Args:
            element: BeautifulSoup Tag object.
            stats: Statistics object to update.
        """
        if not hasattr(element, "attrs"):
            return

        attrs_to_remove = []

        for attr_name, attr_value in list(element.attrs.items()):
            attr_lower = attr_name.lower()

            # Never remove selection marker
            if attr_lower == SELECTION_MARKER_ATTR:
                continue

            # Check keep list
            if attr_lower in KEEP_ATTRIBUTES:
                # Still clean the value
                if attr_lower == "class" and self.config.clean_classes:
                    element[attr_name] = self._filter_classes(attr_value)
                continue

            # Check keep patterns
            if any(attr_lower.startswith(prefix) for prefix in KEEP_ATTRIBUTE_PREFIXES):
                continue

            # Check remove list
            if attr_lower in REMOVE_ATTRIBUTES:
                attrs_to_remove.append(attr_name)
                stats.attrs_cleaned += 1
                continue

            # Check for event handlers (on*)
            if attr_lower.startswith("on"):
                attrs_to_remove.append(attr_name)
                stats.attrs_cleaned += 1
                continue

            # Check for base64 data URLs
            if isinstance(attr_value, str):
                if attr_value.startswith("data:") and ";base64," in attr_value:
                    attrs_to_remove.append(attr_name)
                    stats.base64_removed += 1
                    continue

                # Check for tracking URLs
                if self.config.clean_tracking_urls and self._is_tracking_url(attr_value):
                    attrs_to_remove.append(attr_name)
                    stats.tracking_removed += 1
                    continue

                # Truncate long attribute values
                if len(attr_value) > self.config.max_attribute_length:
                    if attr_lower in ("href", "src"):
                        element[attr_name] = attr_value[:self.config.max_url_length] + "..."
                    else:
                        element[attr_name] = attr_value[:self.config.max_attribute_length] + "..."
                    stats.attrs_cleaned += 1

        # Remove collected attributes
        for attr_name in attrs_to_remove:
            del element[attr_name]

    def _filter_classes(self, class_value) -> str:
        """Filter CSS classes, removing generated ones.

        Args:
            class_value: Class attribute value (string or list).

        Returns:
            Filtered class string.
        """
        if isinstance(class_value, list):
            classes = class_value
        else:
            classes = str(class_value).split()

        kept = []
        for cls in classes:
            # Remove hash classes
            if any(p.match(cls) for p in HASH_CLASS_PATTERNS):
                continue

            # Keep semantic classes
            if any(p.match(cls) for p in SEMANTIC_CLASS_PATTERNS):
                kept.append(cls)
                continue

            # Remove utility classes
            if any(p.match(cls) for p in UTILITY_CLASS_PATTERNS):
                continue

            # Keep classes with vowels (likely meaningful)
            if len(cls) >= 3 and re.search(r'[aeiou]', cls, re.IGNORECASE):
                kept.append(cls)

        return " ".join(kept)

    def _is_tracking_url(self, url: str) -> bool:
        """Check if a URL is a tracking/analytics URL.

        Args:
            url: URL string to check.

        Returns:
            True if URL appears to be for tracking.
        """
        if len(url) < 20:
            return False

        return any(p.search(url) for p in TRACKING_URL_PATTERNS)

    def remove_comments(self, soup: BeautifulSoup, stats: CleaningStats) -> None:
        """Remove HTML comments from the document.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
        """
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
            stats.comments_removed += 1

    def remove_empty_elements(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        preserved: Optional[Set[Tag]] = None,
    ) -> None:
        """Remove empty elements iteratively.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            preserved: Set of elements to preserve.
        """
        preserved = preserved or set()

        for _ in range(self.config.max_empty_iterations):
            removed = 0

            for tag_name in EMPTY_REMOVAL_TAGS:
                for element in soup.find_all(tag_name):
                    if element in preserved:
                        continue

                    if element.name in VOID_ELEMENTS:
                        continue

                    # Check for plugin marker
                    if element.get(SELECTION_MARKER_ATTR):
                        continue

                    text = element.get_text(strip=True)
                    if not text and not element.find_all(True):
                        element.decompose()
                        removed += 1
                        stats.empty_removed += 1

            if removed == 0:
                break

    def truncate_long_texts(
        self,
        soup: BeautifulSoup,
        stats: CleaningStats,
        preserved: Optional[Set[Tag]] = None,
    ) -> None:
        """Truncate long text nodes.

        Args:
            soup: BeautifulSoup object to modify.
            stats: Statistics object to update.
            preserved: Set of elements to preserve.
        """
        preserved = preserved or set()
        max_length = self.config.max_text_length

        for element in soup.find_all(string=True):
            if element.parent in preserved:
                continue

            text = str(element)
            if len(text) > max_length:
                truncated = self._truncate_text(text, max_length)
                element.replace_with(truncated)
                stats.texts_truncated += 1

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text at natural break points.

        Args:
            text: Text to truncate.
            max_length: Maximum length.

        Returns:
            Truncated text.
        """
        if len(text) <= max_length:
            return text

        threshold = int(max_length * 0.8)

        # Try sentence break
        for punct in [".", "?", "!"]:
            idx = text[:threshold].rfind(punct)
            if idx > max_length // 4:
                return text[:idx + 1].strip()

        # Try word break
        idx = text[:threshold].rfind(" ")
        if idx > max_length // 4:
            return text[:idx].strip() + "..."

        # Hard truncation
        return text[:max_length - 3] + "..."

    def decode_entities(self, soup: BeautifulSoup) -> None:
        """Decode HTML entities in text nodes.

        Args:
            soup: BeautifulSoup object to modify.
        """
        if not self.config.decode_entities:
            return

        for element in soup.find_all(string=True):
            text = str(element)
            decoded = self._decode_html_entities(text)
            if decoded != text:
                element.replace_with(decoded)

    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities to characters.

        Protects structural entities (&lt;, &gt;, &amp;).

        Args:
            text: Text with HTML entities.

        Returns:
            Text with entities decoded.
        """
        # Protect structural entities
        for entity, placeholder in PROTECTED_ENTITIES.items():
            text = text.replace(entity, placeholder)

        # Decode common named entities
        for entity, char in COMMON_ENTITIES.items():
            text = text.replace(entity, char)

        # Decode numeric entities
        def decode_numeric(match):
            try:
                return chr(int(match.group(1)))
            except (ValueError, OverflowError):
                return match.group(0)

        text = re.sub(r'&#(\d+);', decode_numeric, text)

        # Decode hex entities
        def decode_hex(match):
            try:
                return chr(int(match.group(1), 16))
            except (ValueError, OverflowError):
                return match.group(0)

        text = re.sub(r'&#x([0-9a-fA-F]+);', decode_hex, text)

        # Restore protected entities
        for entity, placeholder in PROTECTED_ENTITIES.items():
            text = text.replace(placeholder, entity)

        return text

    def clean_whitespace(self, soup: BeautifulSoup) -> None:
        """Clean excessive whitespace from the document.

        Args:
            soup: BeautifulSoup object to modify.
        """
        for element in soup.find_all(string=True):
            text = str(element)
            # Collapse multiple whitespace
            cleaned = re.sub(r'\s+', ' ', text)
            if cleaned != text:
                element.replace_with(cleaned)

    def get_stats(self, original: str, cleaned: str) -> CleaningStats:
        """Calculate cleaning statistics.

        Args:
            original: Original HTML string.
            cleaned: Cleaned HTML string.

        Returns:
            CleaningStats with size information.
        """
        stats = CleaningStats()
        stats.original_size = len(original)
        stats.cleaned_size = len(cleaned)
        return stats


class HTMLCleaner(HTMLCleanerCore):
    """High-level HTML cleaner with convenience methods."""

    def clean_aggressive(self, html: str) -> CleaningResult:
        """Stage 1: Maximum compression for page detection.

        Removes all scripts (except JSON), styles, forms, media,
        and other non-essential content.

        Args:
            html: Raw HTML string.

        Returns:
            CleaningResult with cleaned HTML and statistics.
        """
        from .aggressive import AggressiveCleaner
        cleaner = AggressiveCleaner(self.config)
        return cleaner.clean(html)

    def clean_focused(
        self,
        html: str,
        preserved_selectors: Optional[list] = None,
    ) -> CleaningResult:
        """Stage 2: Context-aware cleaning with element preservation.

        Preserves elements matching the given selectors and their
        surrounding context.

        Args:
            html: Raw HTML string.
            preserved_selectors: CSS selectors for elements to preserve.

        Returns:
            CleaningResult with cleaned HTML and statistics.
        """
        from .focused import FocusedCleaner
        cleaner = FocusedCleaner(self.config)
        return cleaner.clean(html, preserved_selectors)

    def quick_clean(self, html: str) -> str:
        """Fast cleaning without full processing.

        Removes obvious noise quickly without detailed analysis.

        Args:
            html: Raw HTML string.

        Returns:
            Cleaned HTML string.
        """
        soup = self.parse_html(html)

        # Quick removals
        for tag in ["script", "style", "noscript", "link", "iframe"]:
            for element in soup.find_all(tag):
                # Preserve JSON scripts
                if tag == "script" and is_json_script(element):
                    continue
                element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Quick noise selector removal
        quick_selectors = [
            ".cookie-banner", ".ads", ".popup", ".modal",
            ".advertisement", ".sponsored",
        ]
        for selector in quick_selectors:
            try:
                for el in soup.select(selector):
                    el.decompose()
            except Exception:
                pass

        return str(soup)
