"""XTree hierarchical representation exporter.

Converts HTML to a visual tree format showing element
relationships and structure.

Example output:
    ROOT
    ├─ nav#main-nav
    │  ├─ a.nav-link[0] → "Home"
    │  └─ a.nav-link[1] → "Products"
    └─ main
       └─ div.product-list
          ├─ div.product-card[0]
          │  ├─ h3.title → "Product 1"
          │  └─ span.price → "$99.99"
          └─ div.product-card[1]
             └─ ...
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup, Tag


@dataclass
class XTreeConfig:
    """Configuration for XTree export."""

    max_depth: int = 15
    """Maximum tree depth to display."""

    max_children: int = 10
    """Maximum children to show per element."""

    show_text: bool = True
    """Show text content."""

    max_text_length: int = 50
    """Maximum text length before truncation."""

    show_attributes: bool = True
    """Show relevant attributes."""

    use_unicode: bool = True
    """Use Unicode box-drawing characters."""

    collapse_similar: bool = True
    """Collapse consecutive similar elements."""

    filter_empty: bool = True
    """Filter out empty elements."""


# Box-drawing characters
CHARS_UNICODE = {
    'branch': '├─',
    'last': '└─',
    'vertical': '│ ',
    'space': '  ',
    'arrow': '→',
    'ellipsis': '…',
}

CHARS_ASCII = {
    'branch': '+-',
    'last': '\\-',
    'vertical': '| ',
    'space': '  ',
    'arrow': '->',
    'ellipsis': '...',
}


class XTreeExporter:
    """Export HTML as XTree hierarchical format.

    Creates a visual tree representation showing element
    relationships and structure.

    Example:
        exporter = XTreeExporter()
        tree = exporter.export(soup)
    """

    def __init__(self, config: XTreeConfig | None = None):
        """Initialize exporter.

        Args:
            config: Optional configuration.
        """
        self.config = config if config is not None else XTreeConfig()

    def export(
        self,
        soup: BeautifulSoup,
        config: XTreeConfig | None = None,
    ) -> str:
        """Export HTML to XTree format.

        Args:
            soup: BeautifulSoup document.
            config: Optional config override.

        Returns:
            XTree string representation.
        """
        config = config if config is not None else self.config
        chars = CHARS_UNICODE if config.use_unicode else CHARS_ASCII

        lines: List[str] = []
        lines.append('ROOT')

        # Find body or root
        body = soup.find('body')
        if body and isinstance(body, Tag):
            root = body
        else:
            root = None

        if root:
            children = self._get_children(root, config)
            self._render_children(children, lines, '', config, chars)
        else:
            all_children: List[Tag] = []
            for child in soup.children:
                if isinstance(child, Tag):
                    all_children.append(child)
            self._render_children(all_children, lines, '', config, chars)

        return '\n'.join(lines)

    def _get_children(self, element: Tag, config: XTreeConfig) -> List[Tag]:
        """Get visible children of an element.

        Args:
            element: Parent element.
            config: Configuration.

        Returns:
            List of child tags.
        """
        children = []

        for child in element.children:
            if not isinstance(child, Tag):
                continue

            # Skip invisible elements
            if child.name in ('script', 'style', 'meta', 'link', 'noscript', 'template'):
                continue

            # Skip empty elements if configured
            if config.filter_empty:
                if not child.get_text(strip=True) and not self._get_children(child, config):
                    continue

            children.append(child)

        return children

    def _render_children(
        self,
        children: List[Tag],
        lines: List[str],
        prefix: str,
        config: XTreeConfig,
        chars: dict,
    ) -> None:
        """Render child elements.

        Args:
            children: Child elements.
            lines: Output lines.
            prefix: Current line prefix.
            config: Configuration.
            chars: Box-drawing characters.
        """
        # Limit children if needed
        total = len(children)
        if total > config.max_children:
            children = children[:config.max_children]
            truncated = True
        else:
            truncated = False

        # Group similar consecutive children if configured
        if config.collapse_similar:
            children = self._collapse_similar(children, config)

        for i, child in enumerate(children):
            is_last = (i == len(children) - 1) and not truncated

            # Choose branch character
            if is_last:
                branch = chars['last']
                child_prefix = prefix + chars['space']
            else:
                branch = chars['branch']
                child_prefix = prefix + chars['vertical']

            # Build node string
            node = self._format_node(child, config, chars)
            lines.append(f'{prefix}{branch} {node}')

            # Render children recursively
            depth = len(prefix) // 2
            if depth < config.max_depth:
                grandchildren = self._get_children(child, config)
                if grandchildren:
                    self._render_children(grandchildren, lines, child_prefix, config, chars)

        # Add truncation indicator
        if truncated:
            lines.append(f'{prefix}{chars["last"]} {chars["ellipsis"]} ({total - config.max_children} more)')

    def _format_node(self, element: Tag, config: XTreeConfig, chars: dict) -> str:
        """Format a single node.

        Args:
            element: Element to format.
            config: Configuration.
            chars: Box-drawing characters.

        Returns:
            Formatted node string.
        """
        parts: List[str] = []

        # Tag name
        tag = element.name

        # ID
        el_id = element.get('id')
        if el_id and isinstance(el_id, str):
            tag += f'#{el_id}'

        # Classes (filtered)
        classes = element.get('class')
        if classes and isinstance(classes, list):
            # Filter out hash classes
            semantic_classes = []
            for cls in classes:
                if not re.match(r'^(css-|sc-|_[a-z0-9]{4,}|[a-f0-9]{8,})', str(cls), re.I):
                    semantic_classes.append(str(cls))
                    if len(semantic_classes) >= 2:
                        break

            if semantic_classes:
                tag += '.' + '.'.join(semantic_classes)

        parts.append(tag)

        # Key attributes
        if config.show_attributes:
            attrs = self._get_key_attributes(element)
            if attrs:
                parts.append(f'[{", ".join(attrs)}]')

        # Text content
        if config.show_text:
            text = self._get_short_text(element, config.max_text_length)
            if text:
                parts.append(f'{chars["arrow"]} "{text}"')

        return ' '.join(parts)

    def _get_key_attributes(self, element: Tag) -> List[str]:
        """Get key attributes for display.

        Args:
            element: Element to get attributes from.

        Returns:
            List of attribute strings.
        """
        attrs = []

        # Type (for inputs)
        if element.name == 'input':
            input_type = element.get('type')
            if input_type and input_type != 'text':
                attrs.append(f'type={input_type}')

        # Role
        role = element.get('role')
        if role:
            attrs.append(f'role={role}')

        # ARIA states
        if element.get('aria-expanded'):
            attrs.append(f'expanded={element.get("aria-expanded")}')
        if element.has_attr('disabled'):
            attrs.append('disabled')
        if element.has_attr('checked'):
            attrs.append('checked')

        # Data-testid
        testid = element.get('data-testid')
        if testid:
            attrs.append(f'testid={testid}')

        return attrs

    def _get_short_text(self, element: Tag, max_length: int) -> str:
        """Get short text content.

        Args:
            element: Element to get text from.
            max_length: Maximum length.

        Returns:
            Truncated text or empty string.
        """
        # Only get text for leaf nodes or semantic elements
        children = [c for c in element.children if isinstance(c, Tag)]

        if children and element.name not in ('button', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label'):
            return ""

        text = element.get_text(strip=True)
        if not text:
            return ""

        # Clean whitespace
        text = ' '.join(text.split())

        if len(text) <= max_length:
            return text

        return text[:max_length - 3] + '...'

    def _collapse_similar(self, children: List[Tag], config: XTreeConfig) -> List[Tag]:
        """Collapse consecutive similar elements.

        Args:
            children: List of children.
            config: Configuration.

        Returns:
            Collapsed list.
        """
        if not children:
            return children

        result: List[Tag] = []
        similar_count = 1
        prev_sig = None

        for child in children:
            sig = self._get_signature(child)

            if sig == prev_sig and similar_count < 3:
                similar_count += 1
            else:
                if prev_sig and similar_count > 2:
                    # Mark last element as collapsed
                    pass
                result.append(child)
                similar_count = 1

            prev_sig = sig

        return result

    def _get_signature(self, element: Tag) -> str:
        """Get signature for similarity comparison.

        Args:
            element: Element to get signature for.

        Returns:
            Signature string.
        """
        tag = element.name

        classes = element.get('class')
        if classes and isinstance(classes, list):
            # Use first non-hash class
            for cls in classes:
                if not re.match(r'^(css-|sc-|_[a-z0-9]{4,})', str(cls), re.I):
                    return f'{tag}.{cls}'

        return tag


# =============================================================================
# Convenience Functions
# =============================================================================

def to_xtree(
    html: str,
    max_depth: int = 15,
    show_text: bool = True,
    use_unicode: bool = True,
) -> str:
    """Convert HTML to XTree format (convenience function).

    Args:
        html: HTML string to convert.
        max_depth: Maximum tree depth.
        show_text: Show text content.
        use_unicode: Use Unicode box-drawing characters.

    Returns:
        XTree string representation.
    """
    soup = BeautifulSoup(html, 'lxml')
    config = XTreeConfig(
        max_depth=max_depth,
        show_text=show_text,
        use_unicode=use_unicode,
    )
    return XTreeExporter(config).export(soup)
