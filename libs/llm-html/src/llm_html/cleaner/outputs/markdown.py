"""Markdown exporter for cleaned HTML.

Converts HTML to LLM-friendly Markdown format, preserving
structure while removing unnecessary formatting.

Example output:
    # Product List

    ## Product 1
    **Price:** $99.99
    A great product for everyday use.

    [Add to Cart](javascript:void(0))

    ## Product 2
    **Price:** $149.99
    Premium quality item.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


@dataclass
class MarkdownConfig:
    """Configuration for Markdown export."""

    include_links: bool = True
    """Include hyperlinks in output."""

    include_images: bool = False
    """Include image references."""

    preserve_tables: bool = True
    """Convert tables to Markdown tables."""

    max_heading_level: int = 6
    """Maximum heading level to use."""

    code_block_style: str = "fenced"
    """Code block style: 'fenced' or 'indented'."""

    list_marker: str = "-"
    """List marker to use: '-', '*', or '+'."""

    emphasis_marker: str = "*"
    """Emphasis marker: '*' or '_'."""

    strong_marker: str = "**"
    """Strong emphasis marker: '**' or '__'."""

    horizontal_rule: str = "---"
    """Horizontal rule style."""

    strip_comments: bool = True
    """Remove HTML comments."""

    max_line_length: int = 0
    """Max line length (0 = no limit)."""


class MarkdownExporter:
    """Export HTML as Markdown.

    Converts cleaned HTML to a readable Markdown format
    suitable for LLM processing.

    Example:
        exporter = MarkdownExporter()
        markdown = exporter.export(soup)
    """

    def __init__(self, config: MarkdownConfig | None = None):
        """Initialize exporter.

        Args:
            config: Optional configuration.
        """
        self.config = config if config is not None else MarkdownConfig()

    def export(
        self,
        soup: BeautifulSoup,
        config: MarkdownConfig | None = None,
    ) -> str:
        """Export HTML to Markdown.

        Args:
            soup: BeautifulSoup document.
            config: Optional config override.

        Returns:
            Markdown string.
        """
        config = config if config is not None else self.config

        # Find body or root
        body = soup.find('body')
        if body and isinstance(body, Tag):
            root = body
        else:
            root = None

        # Process content
        lines: List[str] = []
        if root:
            self._process_element(root, lines, config)
        else:
            for child in soup.children:
                if isinstance(child, Tag):
                    self._process_element(child, lines, config)

        # Clean up output
        result = '\n'.join(lines)

        # Remove excessive blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()

    def _process_element(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
        in_list: bool = False,
        list_depth: int = 0,
    ) -> None:
        """Process element and children.

        Args:
            element: Element to process.
            lines: Output lines.
            config: Configuration.
            in_list: Whether inside a list.
            list_depth: Current list nesting depth.
        """
        if not isinstance(element, Tag):
            return

        tag = element.name.lower() if element.name else ''

        # Skip invisible elements
        if tag in ('script', 'style', 'meta', 'link', 'noscript', 'template', 'head'):
            return

        # Handle specific elements
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._handle_heading(element, lines, config)
        elif tag == 'p':
            self._handle_paragraph(element, lines, config)
        elif tag in ('ul', 'ol'):
            self._handle_list(element, lines, config, tag == 'ol', list_depth)
        elif tag == 'li':
            self._handle_list_item(element, lines, config, in_list, list_depth)
        elif tag == 'a':
            self._handle_link(element, lines, config)
        elif tag == 'img':
            self._handle_image(element, lines, config)
        elif tag == 'table':
            self._handle_table(element, lines, config)
        elif tag == 'blockquote':
            self._handle_blockquote(element, lines, config)
        elif tag in ('pre', 'code'):
            self._handle_code(element, lines, config)
        elif tag == 'hr':
            lines.append('')
            lines.append(config.horizontal_rule)
            lines.append('')
        elif tag == 'br':
            lines.append('')
        elif tag in ('strong', 'b'):
            text = element.get_text(strip=True)
            if text:
                lines.append(f'{config.strong_marker}{text}{config.strong_marker}')
        elif tag in ('em', 'i'):
            text = element.get_text(strip=True)
            if text:
                lines.append(f'{config.emphasis_marker}{text}{config.emphasis_marker}')
        elif tag in ('div', 'section', 'article', 'main', 'aside', 'header', 'footer', 'nav'):
            # Container - process children
            for child in element.children:
                if isinstance(child, Tag):
                    self._process_element(child, lines, config, in_list, list_depth)
                elif isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        lines.append(text)
        elif tag == 'span':
            text = element.get_text(strip=True)
            if text:
                lines.append(text)
        else:
            # Generic - process children
            for child in element.children:
                if isinstance(child, Tag):
                    self._process_element(child, lines, config, in_list, list_depth)
                elif isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text:
                        lines.append(text)

    def _handle_heading(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle heading elements."""
        level = int(element.name[1]) if element.name else 1
        level = min(level, config.max_heading_level)

        text = element.get_text(strip=True)
        if text:
            lines.append('')
            lines.append('#' * level + ' ' + text)
            lines.append('')

    def _handle_paragraph(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle paragraph elements."""
        text = self._get_inline_text(element, config)
        if text:
            lines.append('')
            lines.append(text)
            lines.append('')

    def _handle_list(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
        ordered: bool,
        depth: int,
    ) -> None:
        """Handle list elements."""
        lines.append('')

        items = element.find_all('li', recursive=False)
        for i, item in enumerate(items):
            indent = '  ' * depth
            marker = f'{i + 1}.' if ordered else config.list_marker

            text = self._get_inline_text(item, config)
            if text:
                lines.append(f'{indent}{marker} {text}')

            # Handle nested lists
            for child in item.children:
                if isinstance(child, Tag) and child.name in ('ul', 'ol'):
                    self._handle_list(child, lines, config, child.name == 'ol', depth + 1)

        lines.append('')

    def _handle_list_item(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
        in_list: bool,
        depth: int,
    ) -> None:
        """Handle list item elements (standalone)."""
        if not in_list:
            text = self._get_inline_text(element, config)
            if text:
                lines.append(f'{config.list_marker} {text}')

    def _handle_link(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle link elements."""
        if not config.include_links:
            text = element.get_text(strip=True)
            if text:
                lines.append(text)
            return

        href = element.get('href', '')
        text = element.get_text(strip=True)

        if text and href:
            # Skip javascript: links
            if str(href).startswith('javascript:'):
                lines.append(text)
            else:
                lines.append(f'[{text}]({href})')
        elif text:
            lines.append(text)

    def _handle_image(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle image elements."""
        if not config.include_images:
            return

        src = element.get('src', '')
        alt = element.get('alt', 'image')

        if src:
            lines.append(f'![{alt}]({src})')

    def _handle_table(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle table elements."""
        if not config.preserve_tables:
            # Just extract text
            text = element.get_text(strip=True)
            if text:
                lines.append(text)
            return

        lines.append('')

        # Get headers
        headers: List[str] = []
        thead = element.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row and isinstance(header_row, Tag):
                headers = [
                    th.get_text(strip=True)
                    for th in header_row.find_all(['th', 'td'])
                    if isinstance(th, Tag)
                ]

        # If no thead, try first row
        if not headers:
            first_row = element.find('tr')
            if first_row and isinstance(first_row, Tag):
                ths = first_row.find_all('th')
                if ths:
                    headers = [th.get_text(strip=True) for th in ths if isinstance(th, Tag)]

        # Get body rows
        rows: List[List[str]] = []
        tbody = element.find('tbody') or element
        for tr in tbody.find_all('tr'):
            if not isinstance(tr, Tag):
                continue
            cells = [
                td.get_text(strip=True)
                for td in tr.find_all(['td', 'th'])
                if isinstance(td, Tag)
            ]
            if cells:
                # Skip header row if already captured
                if cells != headers:
                    rows.append(cells)

        # Build table
        if headers:
            lines.append('| ' + ' | '.join(headers) + ' |')
            lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')

        for row in rows:
            # Pad row to match header length
            while len(row) < len(headers):
                row.append('')
            lines.append('| ' + ' | '.join(row) + ' |')

        lines.append('')

    def _handle_blockquote(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle blockquote elements."""
        lines.append('')

        text = element.get_text(strip=True)
        if text:
            # Split into lines and prefix with >
            for line in text.split('\n'):
                lines.append(f'> {line.strip()}')

        lines.append('')

    def _handle_code(
        self,
        element: Tag,
        lines: List[str],
        config: MarkdownConfig,
    ) -> None:
        """Handle code elements."""
        code = element.get_text()

        # Check if inside <pre>
        parent = element.parent
        is_block = element.name == 'pre' or (parent and isinstance(parent, Tag) and parent.name == 'pre')

        if is_block:
            lines.append('')
            if config.code_block_style == 'fenced':
                # Try to detect language
                lang = ''
                classes = element.get('class', [])
                if isinstance(classes, list):
                    for cls in classes:
                        if str(cls).startswith('language-'):
                            lang = str(cls)[9:]
                            break

                lines.append(f'```{lang}')
                lines.append(code.strip())
                lines.append('```')
            else:
                # Indented style
                for line in code.strip().split('\n'):
                    lines.append('    ' + line)
            lines.append('')
        else:
            # Inline code
            lines.append(f'`{code.strip()}`')

    def _get_inline_text(self, element: Tag, config: MarkdownConfig) -> str:
        """Get inline text with formatting preserved.

        Args:
            element: Element to get text from.
            config: Configuration.

        Returns:
            Formatted text string.
        """
        parts: List[str] = []

        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                if child.name in ('strong', 'b'):
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(f'{config.strong_marker}{text}{config.strong_marker}')
                elif child.name in ('em', 'i'):
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(f'{config.emphasis_marker}{text}{config.emphasis_marker}')
                elif child.name == 'code':
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(f'`{text}`')
                elif child.name == 'a' and config.include_links:
                    href = child.get('href', '')
                    text = child.get_text(strip=True)
                    if text and href and not str(href).startswith('javascript:'):
                        parts.append(f'[{text}]({href})')
                    elif text:
                        parts.append(text)
                elif child.name == 'br':
                    parts.append('\n')
                else:
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(text)

        return ' '.join(parts)


# =============================================================================
# Convenience Functions
# =============================================================================

def to_markdown(
    html: str,
    include_links: bool = True,
    include_images: bool = False,
    preserve_tables: bool = True,
) -> str:
    """Convert HTML to Markdown (convenience function).

    Args:
        html: HTML string to convert.
        include_links: Include hyperlinks.
        include_images: Include images.
        preserve_tables: Convert tables to Markdown tables.

    Returns:
        Markdown string.
    """
    soup = BeautifulSoup(html, 'lxml')
    config = MarkdownConfig(
        include_links=include_links,
        include_images=include_images,
        preserve_tables=preserve_tables,
    )
    return MarkdownExporter(config).export(soup)
