"""D2Snap DOM Downsampling for LLM-optimized HTML.

Implements adaptive DOM downsampling based on the D2Snap research:
"D2Snap locally consolidates nodes by merging container elements
while preserving interactive targets."

Key concepts:
- Token budget targeting: Aim for specific token count
- UI Feature Scoring: Score elements by importance to UI understanding
- Container Consolidation: Merge nested divs/spans without semantic value
- Interactive Preservation: Keep buttons, links, inputs
- Semantic Preservation: Keep article, main, nav, etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


@dataclass
class D2SnapConfig:
    """Configuration for D2Snap downsampling."""

    target_tokens: int = 10000
    """Target token count for output. Approximately 4 chars per token."""

    min_score_threshold: float = 0.2
    """Minimum UI feature score to keep an element."""

    consolidation_depth: int = 3
    """Maximum nesting depth before forcing consolidation."""

    max_repetitions: int = 5
    """Maximum repeated similar elements to keep."""

    preserve_text_ratio: float = 0.7
    """Ratio of text content to preserve (0.0 to 1.0)."""

    aggressive: bool = False
    """Enable aggressive downsampling for very large pages."""


@dataclass
class DownsampleStats:
    """Statistics from downsampling operation."""

    original_elements: int = 0
    """Total elements before downsampling."""

    remaining_elements: int = 0
    """Total elements after downsampling."""

    consolidated_containers: int = 0
    """Number of container elements merged."""

    removed_low_score: int = 0
    """Elements removed due to low UI feature score."""

    truncated_repetitions: int = 0
    """Repeated elements that were truncated."""

    estimated_original_tokens: int = 0
    """Estimated tokens before downsampling."""

    estimated_final_tokens: int = 0
    """Estimated tokens after downsampling."""

    @property
    def reduction_ratio(self) -> float:
        """Calculate reduction ratio."""
        if self.estimated_original_tokens == 0:
            return 0.0
        return 1 - (self.estimated_final_tokens / self.estimated_original_tokens)


@dataclass
class DownsampleResult:
    """Result of D2Snap downsampling."""

    soup: BeautifulSoup
    """The downsampled BeautifulSoup object."""

    stats: DownsampleStats = field(default_factory=DownsampleStats)
    """Downsampling statistics."""

    within_budget: bool = True
    """Whether result is within token budget."""


# =============================================================================
# Element Classifications
# =============================================================================

# Interactive elements - highest preservation priority
INTERACTIVE_ELEMENTS = frozenset({
    'a', 'button', 'input', 'select', 'textarea', 'option',
    'details', 'summary', 'dialog', 'menu', 'menuitem',
})

# Semantic container elements - high preservation priority
SEMANTIC_ELEMENTS = frozenset({
    'article', 'main', 'nav', 'header', 'footer', 'aside',
    'section', 'figure', 'figcaption', 'address', 'time',
})

# Form elements - preserve for accessibility
FORM_ELEMENTS = frozenset({
    'form', 'fieldset', 'legend', 'label', 'datalist',
    'output', 'progress', 'meter',
})

# Table elements - preserve structure
TABLE_ELEMENTS = frozenset({
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'caption', 'colgroup', 'col',
})

# List elements - preserve structure
LIST_ELEMENTS = frozenset({
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
})

# Content elements - medium priority
CONTENT_ELEMENTS = frozenset({
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'pre', 'code', 'blockquote', 'cite',
    'img', 'picture', 'video', 'audio', 'canvas', 'svg',
})

# Generic containers - low priority, candidates for consolidation
GENERIC_CONTAINERS = frozenset({
    'div', 'span',
})

# Stable attribute patterns
STABLE_ID_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')
TEST_ID_ATTRS = frozenset({'data-testid', 'data-test-id', 'data-cy', 'data-test'})


# =============================================================================
# UI Feature Scoring
# =============================================================================

def calculate_ui_feature_score(element: Tag) -> float:
    """Calculate UI feature importance score for an element.

    Higher scores indicate more important elements for UI understanding.

    Args:
        element: BeautifulSoup Tag element.

    Returns:
        Score from 0.0 to 1.0.
    """
    score = 0.0

    tag_name = element.name.lower() if element.name else ''

    # Interactive elements: highest score
    if tag_name in INTERACTIVE_ELEMENTS:
        score += 0.8

    # Semantic elements: high score
    if tag_name in SEMANTIC_ELEMENTS:
        score += 0.6

    # Form elements: medium-high score
    if tag_name in FORM_ELEMENTS:
        score += 0.5

    # Table elements: medium score (preserve structure)
    if tag_name in TABLE_ELEMENTS:
        score += 0.4

    # List elements: medium score
    if tag_name in LIST_ELEMENTS:
        score += 0.4

    # Content elements: medium score
    if tag_name in CONTENT_ELEMENTS:
        score += 0.5

    # Headings get extra score
    if tag_name in ('h1', 'h2', 'h3'):
        score += 0.3

    # Has stable identifier: high score
    element_id = element.get('id', '')
    if element_id and STABLE_ID_PATTERN.match(str(element_id)):
        score += 0.7

    # Has test ID: high score
    for attr in TEST_ID_ATTRS:
        if element.get(attr):
            score += 0.6
            break

    # Has ARIA role or label: medium score
    if element.get('role'):
        score += 0.4
    if element.get('aria-label') or element.get('aria-labelledby'):
        score += 0.3

    # Has name attribute (forms): medium score
    if element.get('name'):
        score += 0.3

    # Has href (links): medium score
    if element.get('href'):
        score += 0.3

    # Has onclick or other event handlers: medium score
    for attr in element.attrs:
        if str(attr).startswith('on'):
            score += 0.2
            break

    # Text content contribution
    text = element.get_text(strip=True)
    text_len = len(text)
    if text_len > 0:
        # Non-empty text gets a score boost
        score += min(0.3, text_len / 500)

    # Generic containers get penalty
    if tag_name in GENERIC_CONTAINERS:
        # But only if they have no other signals
        if score < 0.3:
            score -= 0.1

    return min(1.0, max(0.0, score))


def is_essential_element(element: Tag) -> bool:
    """Check if element is essential and should never be removed.

    Args:
        element: BeautifulSoup Tag element.

    Returns:
        True if element should always be preserved.
    """
    tag_name = element.name.lower() if element.name else ''

    # Always preserve interactive elements
    if tag_name in INTERACTIVE_ELEMENTS:
        return True

    # Always preserve elements with IDs
    if element.get('id'):
        return True

    # Always preserve elements with test IDs
    for attr in TEST_ID_ATTRS:
        if element.get(attr):
            return True

    # Always preserve form-related elements
    if tag_name in FORM_ELEMENTS:
        return True

    return False


# =============================================================================
# D2Snap Downsampler
# =============================================================================

class D2SnapDownsampler:
    """Adaptive DOM downsampling algorithm.

    Reduces DOM size while preserving:
    - Interactive elements (button, a, input)
    - Semantic containers (article, main, section)
    - Elements with stable identifiers (id, data-testid)
    - Important text content

    Example:
        downsampler = D2SnapDownsampler()
        result = downsampler.downsample(soup, config=D2SnapConfig(target_tokens=8000))

        if result.within_budget:
            print(f"Reduced by {result.stats.reduction_ratio:.1%}")
    """

    def __init__(self, config: D2SnapConfig | None = None):
        """Initialize downsampler.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config if config is not None else D2SnapConfig()

    def downsample(
        self,
        soup: BeautifulSoup,
        config: D2SnapConfig | None = None,
    ) -> DownsampleResult:
        """Downsample DOM to target token budget.

        Args:
            soup: BeautifulSoup document to downsample.
            config: Optional config override.

        Returns:
            DownsampleResult with downsampled soup and statistics.
        """
        config = config if config is not None else self.config
        stats = DownsampleStats()

        # Count original elements
        all_elements = soup.find_all(True)
        stats.original_elements = len(all_elements)
        stats.estimated_original_tokens = self._estimate_tokens(str(soup))

        # Phase 1: Remove low-score elements
        stats.removed_low_score = self._remove_low_score_elements(soup, config)

        # Phase 2: Consolidate containers
        stats.consolidated_containers = self._consolidate_containers(soup, config)

        # Phase 3: Truncate repetitions
        stats.truncated_repetitions = self._truncate_repetitions(soup, config)

        # Phase 4: If still over budget and aggressive, apply more reduction
        if config.aggressive:
            self._aggressive_reduction(soup, config)

        # Final stats
        remaining = soup.find_all(True)
        stats.remaining_elements = len(remaining)
        stats.estimated_final_tokens = self._estimate_tokens(str(soup))

        within_budget = stats.estimated_final_tokens <= config.target_tokens

        return DownsampleResult(
            soup=soup,
            stats=stats,
            within_budget=within_budget,
        )

    def _estimate_tokens(self, html: str) -> int:
        """Estimate token count from HTML string.

        Uses approximation of ~4 characters per token.

        Args:
            html: HTML string.

        Returns:
            Estimated token count.
        """
        return len(html) // 4

    def _remove_low_score_elements(
        self,
        soup: BeautifulSoup,
        config: D2SnapConfig,
    ) -> int:
        """Remove elements with low UI feature scores.

        Args:
            soup: BeautifulSoup document.
            config: Configuration.

        Returns:
            Number of elements removed.
        """
        removed = 0
        threshold = config.min_score_threshold

        # Find candidates for removal (work from leaves up)
        candidates = []
        for element in soup.find_all(True):
            if isinstance(element, Tag):
                score = calculate_ui_feature_score(element)
                if score < threshold and not is_essential_element(element):
                    candidates.append((element, score))

        # Sort by score (lowest first)
        candidates.sort(key=lambda x: x[1])

        # Remove candidates, but preserve parent-child relationships
        for element, score in candidates:
            # Check if still in document (parent might have been removed)
            if element.parent is None:
                continue

            # Check if element is a leaf or has only text children
            has_element_children = any(
                isinstance(child, Tag) for child in element.children
            )

            if not has_element_children:
                # Leaf element - safe to remove
                element.decompose()
                removed += 1
            elif element.name in GENERIC_CONTAINERS:
                # Generic container - unwrap (keep children)
                element.unwrap()
                removed += 1

        return removed

    def _consolidate_containers(
        self,
        soup: BeautifulSoup,
        config: D2SnapConfig,
    ) -> int:
        """Merge nested container elements.

        Consolidates patterns like:
        <div><div><div>content</div></div></div>
        into:
        <div>content</div>

        Args:
            soup: BeautifulSoup document.
            config: Configuration.

        Returns:
            Number of containers consolidated.
        """
        consolidated = 0
        max_depth = config.consolidation_depth

        # Find deeply nested containers
        for _ in range(max_depth):  # Multiple passes
            for element in soup.find_all(GENERIC_CONTAINERS):
                if not isinstance(element, Tag):
                    continue

                # Check if only child is same type of container
                children = [c for c in element.children if isinstance(c, Tag)]
                text_children = [c for c in element.children
                                if isinstance(c, NavigableString) and c.strip()]

                if len(children) == 1 and len(text_children) == 0:
                    child = children[0]
                    if child.name in GENERIC_CONTAINERS:
                        # Check if parent has no special attributes
                        parent_attrs = {k for k in element.attrs if k != 'class'}
                        if not parent_attrs:
                            # Merge: unwrap parent, keeping child
                            element.unwrap()
                            consolidated += 1

        return consolidated

    def _truncate_repetitions(
        self,
        soup: BeautifulSoup,
        config: D2SnapConfig,
    ) -> int:
        """Truncate repeated similar elements.

        For patterns like product cards, keep only first N items.

        Args:
            soup: BeautifulSoup document.
            config: Configuration.

        Returns:
            Number of elements truncated.
        """
        truncated = 0
        max_reps = config.max_repetitions

        # Find parent elements with many similar children
        for parent in soup.find_all(True):
            if not isinstance(parent, Tag):
                continue

            # Group children by their tag and class pattern
            children_by_pattern: dict[str, List[Tag]] = {}

            for child in parent.children:
                if isinstance(child, Tag):
                    pattern = self._get_element_pattern(child)
                    if pattern not in children_by_pattern:
                        children_by_pattern[pattern] = []
                    children_by_pattern[pattern].append(child)

            # Truncate groups with too many items
            for pattern, children in children_by_pattern.items():
                if len(children) > max_reps:
                    # Keep first N, add marker, remove rest
                    for child in children[max_reps:]:
                        child.decompose()
                        truncated += 1

                    # Add truncation marker
                    marker = soup.new_tag('span')
                    marker['data-cmdop-truncated'] = str(len(children) - max_reps)
                    marker.string = f'... ({len(children) - max_reps} more items)'
                    children[max_reps - 1].insert_after(marker)

        return truncated

    def _get_element_pattern(self, element: Tag) -> str:
        """Get a pattern string for grouping similar elements.

        Args:
            element: BeautifulSoup Tag.

        Returns:
            Pattern string for grouping.
        """
        tag = element.name

        # Get first meaningful class
        classes = element.get('class', [])
        if isinstance(classes, list) and classes:
            # Take first non-hash class
            for cls in classes:
                if not re.match(r'^[a-f0-9]{6,}$', str(cls)):
                    return f"{tag}.{cls}"

        return tag

    def _aggressive_reduction(
        self,
        soup: BeautifulSoup,
        config: D2SnapConfig,  # noqa: ARG002
    ) -> None:
        """Apply aggressive reduction for very large pages.

        Args:
            soup: BeautifulSoup document.
            config: Configuration (reserved for future use).
        """
        # Remove all style tags
        for style in soup.find_all('style'):
            style.decompose()

        # Remove all comments
        from bs4 import Comment
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        # Truncate long text nodes
        max_text_len = 500
        for text_node in soup.find_all(string=True):
            if isinstance(text_node, NavigableString):
                text = str(text_node)
                if len(text) > max_text_len:
                    truncated = text[:max_text_len] + '...'
                    text_node.replace_with(truncated)

        # Remove all attributes except essential ones
        essential_attrs = {'id', 'class', 'href', 'src', 'alt', 'name', 'type',
                          'role', 'aria-label', 'data-testid', 'data-cmdop-id'}

        for element in soup.find_all(True):
            if isinstance(element, Tag):
                attrs_to_remove = [
                    attr for attr in element.attrs
                    if attr not in essential_attrs
                    and not attr.startswith('data-cmdop')
                ]
                for attr in attrs_to_remove:
                    del element.attrs[attr]


# =============================================================================
# Convenience Functions
# =============================================================================

def downsample_html(
    html: str,
    target_tokens: int = 10000,
    aggressive: bool = False,
) -> str:
    """Downsample HTML to target token count (convenience function).

    Args:
        html: Raw HTML string.
        target_tokens: Target token count.
        aggressive: Enable aggressive reduction.

    Returns:
        Downsampled HTML string.
    """
    soup = BeautifulSoup(html, 'lxml')
    config = D2SnapConfig(target_tokens=target_tokens, aggressive=aggressive)
    downsampler = D2SnapDownsampler(config)
    result = downsampler.downsample(soup)
    return str(result.soup)


def estimate_tokens(html: str) -> int:
    """Estimate token count for HTML string.

    Args:
        html: HTML string.

    Returns:
        Estimated token count (approximately 4 chars per token).
    """
    return len(html) // 4
