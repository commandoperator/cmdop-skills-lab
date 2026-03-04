"""Semantic chunking for large pages.

Splits large HTML pages into manageable chunks at logical boundaries,
preserving context while staying within token budgets.

Key features:
- Detect repeating item patterns (product cards, list items, etc.)
- Split at semantic boundaries (not mid-element)
- Preserve header/context in each chunk
- Token budget awareness
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


@dataclass
class ChunkConfig:
    """Configuration for semantic chunking."""

    max_tokens: int = 8000
    """Maximum tokens per chunk."""

    min_items: int = 3
    """Minimum items per chunk."""

    max_items: int = 20
    """Maximum items per chunk."""

    preserve_context: bool = True
    """Include header/parent context in each chunk."""

    context_max_tokens: int = 1000
    """Maximum tokens for context section."""


@dataclass
class Chunk:
    """A single chunk of HTML content."""

    html: str
    """The HTML content of this chunk."""

    estimated_tokens: int
    """Estimated token count."""

    item_count: int
    """Number of items in this chunk."""

    container_selector: str
    """CSS selector for the item container."""

    start_index: int
    """Start index of items in original list."""

    end_index: int
    """End index of items in original list (exclusive)."""

    context_html: str = ""
    """Context/header HTML included in chunk."""

    chunk_index: int = 0
    """Index of this chunk (0-based)."""

    total_chunks: int = 1
    """Total number of chunks."""


@dataclass
class ItemPattern:
    """Detected repeating item pattern."""

    selector: str
    """CSS selector for items."""

    count: int
    """Number of items matching this pattern."""

    parent: Tag | None
    """Parent container element."""

    sample_html: str
    """Sample HTML of one item."""

    avg_tokens: int
    """Average tokens per item."""


@dataclass
class ChunkResult:
    """Result of chunking operation."""

    chunks: List[Chunk] = field(default_factory=list)
    """List of content chunks."""

    pattern: ItemPattern | None = None
    """Detected item pattern used for chunking."""

    original_tokens: int = 0
    """Original content token count."""

    was_chunked: bool = False
    """Whether content was actually chunked (vs returned as-is)."""


# =============================================================================
# Pattern Detection
# =============================================================================

# Common item container patterns
ITEM_PATTERNS = [
    # List items
    (r'li', 'ul > li, ol > li'),
    # Table rows
    (r'tr', 'tbody > tr, table > tr'),
    # Cards/items with common class patterns
    (r'\.product', '[class*="product"]'),
    (r'\.item', '[class*="item"]'),
    (r'\.card', '[class*="card"]'),
    (r'\.listing', '[class*="listing"]'),
    (r'\.result', '[class*="result"]'),
    (r'\.entry', '[class*="entry"]'),
    (r'\.post', '[class*="post"]'),
    (r'\.article', 'article'),
    # Grid/flex children
    (r'\.grid', '[class*="grid"] > div'),
    (r'\.flex', '[class*="flex"] > div'),
]


def _estimate_tokens(html: str) -> int:
    """Estimate token count (approximately 4 chars per token)."""
    return len(html) // 4


def _get_selector_for_element(element: Tag) -> str:
    """Generate a CSS selector for an element."""
    parts = [element.name]

    # Add ID if present
    if element.get('id'):
        parts.append(f"#{element['id']}")
        return ''.join(parts)

    # Add first meaningful class
    classes = element.get('class', [])
    if isinstance(classes, list):
        for cls in classes:
            # Skip hash classes
            if not re.match(r'^[a-f0-9]{6,}$', str(cls)):
                parts.append(f".{cls}")
                break

    return ''.join(parts)


def _get_element_signature(element: Tag) -> str:
    """Get a signature for grouping similar elements."""
    tag = element.name

    classes = element.get('class', [])
    if isinstance(classes, list) and classes:
        # Use first non-hash class
        for cls in classes:
            if not re.match(r'^[a-f0-9]{6,}$|^css-|^sc-|^_[a-z0-9]', str(cls), re.I):
                return f"{tag}.{cls}"

    return tag


class SemanticChunker:
    """Split large pages into semantic chunks.

    Designed for e-commerce and listing pages with many repeated items.

    Example:
        chunker = SemanticChunker()
        result = chunker.chunk(soup, config=ChunkConfig(max_tokens=5000))

        for chunk in result.chunks:
            print(f"Chunk {chunk.chunk_index}: {chunk.item_count} items, ~{chunk.estimated_tokens} tokens")
    """

    def __init__(self, config: ChunkConfig | None = None):
        """Initialize chunker.

        Args:
            config: Optional configuration.
        """
        self.config = config if config is not None else ChunkConfig()

    def chunk(
        self,
        soup: BeautifulSoup,
        config: ChunkConfig | None = None,
    ) -> ChunkResult:
        """Chunk HTML content at semantic boundaries.

        Args:
            soup: BeautifulSoup document to chunk.
            config: Optional config override.

        Returns:
            ChunkResult with list of chunks.
        """
        config = config if config is not None else self.config

        # Estimate original tokens
        original_html = str(soup)
        original_tokens = _estimate_tokens(original_html)

        # If already within budget, return as single chunk
        if original_tokens <= config.max_tokens:
            return ChunkResult(
                chunks=[Chunk(
                    html=original_html,
                    estimated_tokens=original_tokens,
                    item_count=0,
                    container_selector="",
                    start_index=0,
                    end_index=0,
                    chunk_index=0,
                    total_chunks=1,
                )],
                original_tokens=original_tokens,
                was_chunked=False,
            )

        # Detect item patterns
        patterns = self.detect_item_patterns(soup)

        if not patterns:
            # No patterns found - return as single chunk
            return ChunkResult(
                chunks=[Chunk(
                    html=original_html,
                    estimated_tokens=original_tokens,
                    item_count=0,
                    container_selector="",
                    start_index=0,
                    end_index=0,
                    chunk_index=0,
                    total_chunks=1,
                )],
                original_tokens=original_tokens,
                was_chunked=False,
            )

        # Use best pattern (most items with reasonable size)
        best_pattern = self._select_best_pattern(patterns, config)

        # Create chunks based on pattern
        chunks = self._create_chunks(soup, best_pattern, config)

        return ChunkResult(
            chunks=chunks,
            pattern=best_pattern,
            original_tokens=original_tokens,
            was_chunked=len(chunks) > 1,
        )

    def detect_item_patterns(self, soup: BeautifulSoup) -> List[ItemPattern]:
        """Detect repeating item patterns in the document.

        Args:
            soup: BeautifulSoup document.

        Returns:
            List of detected item patterns.
        """
        patterns = []

        # Group elements by parent and signature
        parent_children: dict[int, dict[str, List[Tag]]] = {}

        for element in soup.find_all(True):
            if not isinstance(element, Tag):
                continue

            parent = element.parent
            if not parent or not isinstance(parent, Tag):
                continue

            parent_id = id(parent)
            if parent_id not in parent_children:
                parent_children[parent_id] = {}

            sig = _get_element_signature(element)
            if sig not in parent_children[parent_id]:
                parent_children[parent_id][sig] = []
            parent_children[parent_id][sig].append(element)

        # Find groups with enough items
        min_items = 3
        for parent_id, sig_groups in parent_children.items():
            for sig, elements in sig_groups.items():
                if len(elements) >= min_items:
                    # Calculate average tokens
                    total_tokens = sum(_estimate_tokens(str(e)) for e in elements[:5])
                    avg_tokens = total_tokens // min(5, len(elements))

                    parent = elements[0].parent
                    patterns.append(ItemPattern(
                        selector=sig,
                        count=len(elements),
                        parent=parent if isinstance(parent, Tag) else None,
                        sample_html=str(elements[0])[:500],
                        avg_tokens=avg_tokens,
                    ))

        # Sort by count (most items first)
        patterns.sort(key=lambda p: p.count, reverse=True)

        return patterns[:5]  # Return top 5 patterns

    def _select_best_pattern(
        self,
        patterns: List[ItemPattern],
        config: ChunkConfig,
    ) -> ItemPattern:
        """Select the best pattern for chunking.

        Prefers patterns with:
        - Many items
        - Reasonable item size (not too small, not too large)
        """
        if not patterns:
            raise ValueError("No patterns to select from")

        # Score each pattern
        scored = []
        for p in patterns:
            score = 0.0

            # More items = better
            score += min(100, p.count) / 100 * 0.5

            # Ideal item size: 100-500 tokens
            if 100 <= p.avg_tokens <= 500:
                score += 0.3
            elif 50 <= p.avg_tokens <= 1000:
                score += 0.15

            # Items that fit well in chunks
            items_per_chunk = config.max_tokens // max(1, p.avg_tokens)
            if config.min_items <= items_per_chunk <= config.max_items:
                score += 0.2

            scored.append((p, score))

        # Return highest scoring
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _create_chunks(
        self,
        soup: BeautifulSoup,
        pattern: ItemPattern,
        config: ChunkConfig,
    ) -> List[Chunk]:
        """Create chunks based on detected pattern.

        Args:
            soup: BeautifulSoup document.
            pattern: Item pattern to use.
            config: Configuration.

        Returns:
            List of chunks.
        """
        if not pattern.parent:
            return []

        # Find all items matching pattern
        items = list(pattern.parent.children)
        items = [i for i in items if isinstance(i, Tag)]

        if not items:
            return []

        # Calculate items per chunk
        available_tokens = config.max_tokens
        if config.preserve_context:
            available_tokens -= config.context_max_tokens

        items_per_chunk = max(
            config.min_items,
            min(config.max_items, available_tokens // max(1, pattern.avg_tokens))
        )

        # Get context HTML
        context_html = ""
        if config.preserve_context:
            context_html = self._extract_context(soup, pattern.parent)

        # Create chunks
        chunks = []
        total_items = len(items)
        chunk_count = (total_items + items_per_chunk - 1) // items_per_chunk

        for i in range(0, total_items, items_per_chunk):
            chunk_items = items[i:i + items_per_chunk]
            chunk_html = '\n'.join(str(item) for item in chunk_items)

            # Wrap in container
            container_tag = pattern.parent.name
            chunk_html = f"<{container_tag}>{chunk_html}</{container_tag}>"

            if context_html:
                chunk_html = context_html + "\n" + chunk_html

            chunk_index = len(chunks)
            chunks.append(Chunk(
                html=chunk_html,
                estimated_tokens=_estimate_tokens(chunk_html),
                item_count=len(chunk_items),
                container_selector=pattern.selector,
                start_index=i,
                end_index=i + len(chunk_items),
                context_html=context_html,
                chunk_index=chunk_index,
                total_chunks=chunk_count,
            ))

        return chunks

    def _extract_context(self, soup: BeautifulSoup, container: Tag) -> str:
        """Extract context/header HTML to include in chunks.

        Args:
            soup: Full document.
            container: The container element.

        Returns:
            Context HTML string.
        """
        context_parts = []

        # Find header elements before container
        for sibling in container.find_previous_siblings():
            if isinstance(sibling, Tag):
                if sibling.name in ('header', 'nav', 'h1', 'h2', 'h3'):
                    context_parts.insert(0, str(sibling))
                elif sibling.name == 'div' and len(str(sibling)) < 500:
                    # Small divs might be headers
                    context_parts.insert(0, str(sibling))

        # Include document title if available
        title = soup.find('title')
        if title:
            context_parts.insert(0, str(title))

        # Limit context size
        context = '\n'.join(context_parts)
        if _estimate_tokens(context) > 1000:
            # Truncate
            context = context[:4000]

        return context


# =============================================================================
# Convenience Functions
# =============================================================================

def chunk_html(
    html: str,
    max_tokens: int = 8000,
    max_items: int = 20,
) -> List[str]:
    """Chunk HTML into smaller pieces (convenience function).

    Args:
        html: HTML string to chunk.
        max_tokens: Maximum tokens per chunk.
        max_items: Maximum items per chunk.

    Returns:
        List of HTML chunk strings.
    """
    soup = BeautifulSoup(html, 'lxml')
    config = ChunkConfig(max_tokens=max_tokens, max_items=max_items)
    chunker = SemanticChunker(config)
    result = chunker.chunk(soup)
    return [chunk.html for chunk in result.chunks]
