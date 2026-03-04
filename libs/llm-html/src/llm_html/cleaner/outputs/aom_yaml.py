"""Accessibility Object Model (AOM) YAML exporter.

Converts HTML to a Playwright-style Aria Snapshot YAML format.
This provides a compact, accessible-tree representation of the page
that is highly stable and token-efficient for LLM processing.

Example output:
    - navigation:
      - link "Home"
      - link "Products"
    - main:
      - heading "Product List" [level=1]
      - list:
        - listitem:
          - text "Product 1"
          - text "$99.99"
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag


@dataclass
class AOMConfig:
    """Configuration for AOM YAML export."""

    include_text: bool = True
    """Include text content in output."""

    include_attributes: bool = True
    """Include relevant ARIA/semantic attributes."""

    max_text_length: int = 100
    """Maximum text length before truncation."""

    max_depth: int = 20
    """Maximum tree depth to process."""

    skip_empty: bool = True
    """Skip elements with no meaningful content."""

    include_roles: bool = True
    """Include implicit/explicit ARIA roles."""


# Mapping of HTML elements to ARIA roles
IMPLICIT_ROLES: Dict[str, str] = {
    # Landmarks
    'header': 'banner',
    'footer': 'contentinfo',
    'main': 'main',
    'nav': 'navigation',
    'aside': 'complementary',
    'section': 'region',
    'article': 'article',
    'form': 'form',
    'search': 'search',
    # Interactive
    'button': 'button',
    'a': 'link',
    'input': 'textbox',
    'select': 'combobox',
    'textarea': 'textbox',
    'checkbox': 'checkbox',
    'radio': 'radio',
    # Structure
    'h1': 'heading',
    'h2': 'heading',
    'h3': 'heading',
    'h4': 'heading',
    'h5': 'heading',
    'h6': 'heading',
    'ul': 'list',
    'ol': 'list',
    'li': 'listitem',
    'table': 'table',
    'tr': 'row',
    'th': 'columnheader',
    'td': 'cell',
    'img': 'img',
    'figure': 'figure',
    'figcaption': 'caption',
    # Menu
    'menu': 'menu',
    'menuitem': 'menuitem',
    # Dialog
    'dialog': 'dialog',
    'alertdialog': 'alertdialog',
}

# Input type to role mapping
INPUT_ROLES: Dict[str, str] = {
    'button': 'button',
    'submit': 'button',
    'reset': 'button',
    'checkbox': 'checkbox',
    'radio': 'radio',
    'range': 'slider',
    'search': 'searchbox',
    'email': 'textbox',
    'tel': 'textbox',
    'url': 'textbox',
    'number': 'spinbutton',
}


class AOMYAMLExporter:
    """Export HTML as Accessibility Object Model YAML.

    Creates a Playwright-style Aria Snapshot format that provides
    a compact, semantically meaningful representation of the page.

    Example:
        exporter = AOMYAMLExporter()
        yaml_output = exporter.export(soup)

        # Output:
        # - navigation:
        #   - link "Home"
        #   - link "Products"
        # - main:
        #   - heading "Product List" [level=1]
    """

    def __init__(self, config: AOMConfig | None = None):
        """Initialize exporter.

        Args:
            config: Optional configuration.
        """
        self.config = config if config is not None else AOMConfig()

    def export(
        self,
        soup: BeautifulSoup,
        config: AOMConfig | None = None,
    ) -> str:
        """Export HTML to AOM YAML format.

        Args:
            soup: BeautifulSoup document.
            config: Optional config override.

        Returns:
            YAML string representation.
        """
        config = config if config is not None else self.config

        # Find body or root element
        body = soup.find('body')
        if body and isinstance(body, Tag):
            root = body
        else:
            root = None

        # Build tree
        lines: List[str] = []
        if root:
            self._process_element(root, lines, 0, config)
        else:
            # Process children of soup directly
            for child in soup.children:
                if isinstance(child, Tag):
                    self._process_element(child, lines, 0, config)

        return '\n'.join(lines)

    def _process_element(
        self,
        element: Tag,
        lines: List[str],
        depth: int,
        config: AOMConfig,
    ) -> None:
        """Process a single element and its children.

        Args:
            element: Element to process.
            lines: Output lines list.
            depth: Current indentation depth.
            config: Configuration.
        """
        if depth > config.max_depth:
            return

        # Skip non-element nodes
        if not isinstance(element, Tag):
            return

        # Skip invisible elements
        if element.name in ('script', 'style', 'meta', 'link', 'noscript', 'template'):
            return

        # Get role
        role = self._get_role(element)

        # Get accessible name
        name = self._get_accessible_name(element, config)

        # Get attributes
        attrs = self._get_attributes(element, config) if config.include_attributes else {}

        # Check if element has meaningful content
        has_content = bool(name) or bool(attrs) or role is not None

        # Get children that are elements
        children = [c for c in element.children if isinstance(c, Tag)]

        # Skip empty containers with no role
        if config.skip_empty and not has_content and not children:
            return

        # Build output line
        indent = "  " * depth

        if role:
            if name:
                name_escaped = name.replace('"', '\\"')
                line = f'{indent}- {role} "{name_escaped}"'
            else:
                line = f'{indent}- {role}'

            # Add attributes
            if attrs:
                attr_str = ' '.join(f'{k}={v}' for k, v in attrs.items())
                line += f' [{attr_str}]'

            # Add colon if has children
            if children:
                line += ':'

            lines.append(line)

            # Process children
            for child in children:
                self._process_element(child, lines, depth + 1, config)

        else:
            # No role - just process children
            for child in children:
                self._process_element(child, lines, depth, config)

    def _get_role(self, element: Tag) -> Optional[str]:
        """Get ARIA role for element.

        Args:
            element: Element to get role for.

        Returns:
            Role name or None.
        """
        # Explicit role
        explicit_role = element.get('role')
        if explicit_role:
            return str(explicit_role)

        tag = element.name.lower() if element.name else ''

        # Handle input types
        if tag == 'input':
            input_type = element.get('type', 'text')
            if isinstance(input_type, str):
                return INPUT_ROLES.get(input_type.lower(), 'textbox')

        # Handle links
        if tag == 'a' and element.get('href'):
            return 'link'

        # Implicit role
        return IMPLICIT_ROLES.get(tag)

    def _get_accessible_name(self, element: Tag, config: AOMConfig) -> str:
        """Get accessible name for element.

        Priority:
        1. aria-label
        2. aria-labelledby (resolved)
        3. alt (for images)
        4. title
        5. Direct text content
        6. value (for inputs)
        7. placeholder (for inputs)

        Args:
            element: Element to get name for.
            config: Configuration.

        Returns:
            Accessible name string.
        """
        if not config.include_text:
            return ""

        # aria-label
        aria_label = element.get('aria-label')
        if aria_label:
            return self._truncate(str(aria_label), config.max_text_length)

        # alt (for images)
        if element.name == 'img':
            alt = element.get('alt')
            if alt:
                return self._truncate(str(alt), config.max_text_length)

        # title
        title = element.get('title')
        if title and element.name not in ('html', 'head'):
            return self._truncate(str(title), config.max_text_length)

        # Direct text content
        text = element.get_text(strip=True)
        if text:
            # Only use if not too long and element is a leaf or semantic
            if len(text) < 500 or element.name in ('button', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'label'):
                return self._truncate(text, config.max_text_length)

        # value (for inputs)
        if element.name == 'input':
            value = element.get('value')
            if value:
                return self._truncate(str(value), config.max_text_length)

            placeholder = element.get('placeholder')
            if placeholder:
                return self._truncate(f"[{placeholder}]", config.max_text_length)

        return ""

    def _get_attributes(self, element: Tag, config: AOMConfig) -> Dict[str, str]:
        """Get relevant attributes for output.

        Args:
            element: Element to get attributes from.
            config: Configuration.

        Returns:
            Dictionary of attribute key-value pairs.
        """
        attrs = {}

        # Heading level
        if element.name and element.name.startswith('h') and len(element.name) == 2:
            level = element.name[1]
            if level.isdigit():
                attrs['level'] = level

        # Disabled state
        if element.has_attr('disabled'):
            attrs['disabled'] = 'true'

        # Checked state
        if element.has_attr('checked'):
            attrs['checked'] = 'true'

        # Required
        if element.has_attr('required'):
            attrs['required'] = 'true'

        # Expanded
        expanded = element.get('aria-expanded')
        if expanded:
            attrs['expanded'] = str(expanded)

        # Selected
        if element.has_attr('selected') or element.get('aria-selected') == 'true':
            attrs['selected'] = 'true'

        # Current
        current = element.get('aria-current')
        if current and current != 'false':
            attrs['current'] = str(current)

        return attrs

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length.

        Args:
            text: Text to truncate.
            max_length: Maximum length.

        Returns:
            Truncated text.
        """
        # Clean whitespace
        text = ' '.join(text.split())

        if len(text) <= max_length:
            return text

        return text[:max_length - 3] + "..."


# =============================================================================
# Convenience Functions
# =============================================================================

def to_aom_yaml(
    html: str,
    max_text_length: int = 100,
    include_attributes: bool = True,
) -> str:
    """Convert HTML to AOM YAML format (convenience function).

    Args:
        html: HTML string to convert.
        max_text_length: Maximum text length before truncation.
        include_attributes: Include ARIA/semantic attributes.

    Returns:
        YAML string representation.
    """
    soup = BeautifulSoup(html, 'lxml')
    config = AOMConfig(
        max_text_length=max_text_length,
        include_attributes=include_attributes,
    )
    return AOMYAMLExporter(config).export(soup)
