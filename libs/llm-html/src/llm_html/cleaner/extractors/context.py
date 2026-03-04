"""Context Window Extraction for selector generation.

Extracts the optimal "Goldilocks" window around target elements:
- Target element itself
- Immediate parent with key attributes
- Previous/next siblings
- Closest stable ancestor (with id or data-testid)
- CSS path from anchor to target

This provides the minimal context needed for accurate selector generation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from bs4 import BeautifulSoup, Tag


@dataclass
class ContextWindow:
    """Extracted context around a target element."""

    target: str
    """Target element HTML."""

    target_tag: str
    """Tag name of target element."""

    parent: str
    """Parent element HTML (minimal, without full children)."""

    parent_tag: str
    """Tag name of parent element."""

    prev_siblings: List[str] = field(default_factory=list)
    """Previous siblings HTML (minimal)."""

    next_siblings: List[str] = field(default_factory=list)
    """Next siblings HTML (minimal)."""

    anchor_id: Optional[str] = None
    """Stable ancestor ID (id or data-testid)."""

    anchor_tag: str = ""
    """Tag name of anchor element."""

    anchor_path: str = ""
    """CSS path from anchor to target."""

    depth: int = 0
    """Depth from anchor to target."""

    css_selector: str = ""
    """Suggested CSS selector for target."""

    xpath: str = ""
    """XPath expression for target."""


@dataclass
class ContextConfig:
    """Configuration for context extraction."""

    include_parent: bool = True
    """Include parent element context."""

    include_siblings: bool = True
    """Include sibling elements."""

    max_siblings: int = 2
    """Maximum siblings to include on each side."""

    find_stable_anchor: bool = True
    """Find closest ancestor with stable identifier."""

    max_anchor_depth: int = 10
    """Maximum depth to search for stable anchor."""

    minimize_html: bool = True
    """Minimize HTML output (remove unnecessary attributes)."""

    include_text_content: bool = True
    """Include visible text content."""


# Stable identifier patterns
STABLE_ID_PATTERN = re.compile(
    r'^[a-z][a-z0-9_-]*$',
    re.IGNORECASE
)

# Attributes indicating stable identifiers
STABLE_ATTRS = ['id', 'data-testid', 'data-test-id', 'data-cy', 'data-qa']

# Attributes to preserve in minimal HTML
PRESERVE_ATTRS = [
    'id', 'class', 'role', 'aria-label', 'aria-labelledby',
    'data-testid', 'data-test-id', 'data-cy', 'data-qa',
    'href', 'src', 'alt', 'title', 'name', 'type', 'value',
    'placeholder', 'for', 'action', 'method',
]


class ContextExtractor:
    """Extract optimal context around target elements.

    The "Goldilocks" window provides just enough context for accurate
    selector generation without overwhelming the LLM with irrelevant HTML.

    Example:
        extractor = ContextExtractor()
        context = extractor.extract(target_element)

        print(f"Anchor: #{context.anchor_id}")
        print(f"Path: {context.anchor_path}")
        print(f"Selector: {context.css_selector}")
    """

    def __init__(self, config: ContextConfig | None = None):
        """Initialize context extractor.

        Args:
            config: Optional configuration.
        """
        self.config = config if config is not None else ContextConfig()

    def extract(
        self,
        element: Tag,
        config: ContextConfig | None = None,
    ) -> ContextWindow:
        """Extract context window around an element.

        Args:
            element: Target element to extract context for.
            config: Optional config override.

        Returns:
            ContextWindow with extracted context.
        """
        config = config if config is not None else self.config

        # Extract target HTML
        target_html = self._minimize_html(element) if config.minimize_html else str(element)
        target_tag = element.name or ""

        # Extract parent context
        parent_html = ""
        parent_tag = ""
        if config.include_parent and element.parent and isinstance(element.parent, Tag):
            parent_html = self._extract_parent_context(element.parent, element)
            parent_tag = element.parent.name

        # Extract siblings
        prev_siblings: List[str] = []
        next_siblings: List[str] = []
        if config.include_siblings:
            prev_siblings = self._extract_siblings(
                element,
                direction='prev',
                max_count=config.max_siblings,
                minimize=config.minimize_html,
            )
            next_siblings = self._extract_siblings(
                element,
                direction='next',
                max_count=config.max_siblings,
                minimize=config.minimize_html,
            )

        # Find stable anchor
        anchor_id: Optional[str] = None
        anchor_tag = ""
        anchor_path = ""
        depth = 0

        if config.find_stable_anchor:
            anchor, anchor_id, _ = self._find_stable_anchor(
                element,
                max_depth=config.max_anchor_depth,
            )
            if anchor:
                anchor_tag = anchor.name
                anchor_path, depth = self._build_path(anchor, element)

        # Generate selectors
        css_selector = self._generate_css_selector(element, anchor_id, anchor_path)
        xpath = self._generate_xpath(element, anchor_id, anchor_path)

        return ContextWindow(
            target=target_html,
            target_tag=target_tag,
            parent=parent_html,
            parent_tag=parent_tag,
            prev_siblings=prev_siblings,
            next_siblings=next_siblings,
            anchor_id=anchor_id,
            anchor_tag=anchor_tag,
            anchor_path=anchor_path,
            depth=depth,
            css_selector=css_selector,
            xpath=xpath,
        )

    def extract_from_selector(
        self,
        soup: BeautifulSoup,
        selector: str,
        config: ContextConfig | None = None,
    ) -> List[ContextWindow]:
        """Extract context for all elements matching a selector.

        Args:
            soup: BeautifulSoup document.
            selector: CSS selector to match elements.
            config: Optional config override.

        Returns:
            List of ContextWindow objects.
        """
        elements = soup.select(selector)
        return [self.extract(el, config) for el in elements if isinstance(el, Tag)]

    def _minimize_html(self, element: Tag) -> str:
        """Create minimal HTML representation.

        Preserves essential attributes and structure.
        """
        # Create a copy to avoid modifying original
        tag = element.name
        attrs = {}

        # Preserve only essential attributes
        for attr in PRESERVE_ATTRS:
            if element.has_attr(attr):
                value = element[attr]
                if isinstance(value, list):
                    # Filter classes
                    value = ' '.join(self._filter_classes(value))
                attrs[attr] = value

        # Build opening tag
        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items() if v)
        if attr_str:
            open_tag = f"<{tag} {attr_str}>"
        else:
            open_tag = f"<{tag}>"

        # Get text content
        text = element.get_text(strip=True)
        if len(text) > 100:
            text = text[:100] + "..."

        # Check for children
        children = [c for c in element.children if isinstance(c, Tag)]
        if children:
            child_summary = f"[{len(children)} children]"
            return f"{open_tag}{text[:50] if text else ''}{child_summary}</{tag}>"

        return f"{open_tag}{text}</{tag}>"

    def _filter_classes(self, classes: List[str]) -> List[str]:
        """Filter out hash/generated classes."""
        filtered = []
        for cls in classes[:5]:  # Keep max 5 classes
            # Skip hash classes
            if re.match(r'^(css-|sc-|_[a-z0-9]{4,}|[a-f0-9]{8,})', cls, re.I):
                continue
            filtered.append(cls)
        return filtered

    def _extract_parent_context(self, parent: Tag, target: Tag) -> str:
        """Extract parent element context without full children."""
        tag = parent.name
        attrs = {}

        for attr in PRESERVE_ATTRS:
            if parent.has_attr(attr):
                value = parent[attr]
                if isinstance(value, list):
                    value = ' '.join(self._filter_classes(value))
                attrs[attr] = value

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items() if v)
        if attr_str:
            open_tag = f"<{tag} {attr_str}>"
        else:
            open_tag = f"<{tag}>"

        # Count children
        children = [c for c in parent.children if isinstance(c, Tag)]
        child_count = len(children)

        # Find target position
        target_pos = -1
        for i, child in enumerate(children):
            if child is target:
                target_pos = i
                break

        return f"{open_tag}[{child_count} children, target at {target_pos}]</{tag}>"

    def _extract_siblings(
        self,
        element: Tag,
        direction: str,
        max_count: int,
        minimize: bool,
    ) -> List[str]:
        """Extract sibling elements."""
        siblings = []

        if direction == 'prev':
            current = element.find_previous_sibling()
        else:
            current = element.find_next_sibling()

        while current and len(siblings) < max_count:
            if isinstance(current, Tag):
                if minimize:
                    siblings.append(self._minimize_html(current))
                else:
                    siblings.append(str(current))

            if direction == 'prev':
                current = current.find_previous_sibling()
            else:
                current = current.find_next_sibling()

        return siblings

    def _find_stable_anchor(
        self,
        element: Tag,
        max_depth: int,
    ) -> tuple[Tag | None, str | None, str | None]:
        """Find closest ancestor with stable identifier.

        Returns:
            Tuple of (anchor element, id value, attribute name).
        """
        current = element.parent
        depth = 0

        while current and isinstance(current, Tag) and depth < max_depth:
            # Check for stable identifiers
            for attr in STABLE_ATTRS:
                value = current.get(attr)
                if value and isinstance(value, str):
                    # Validate it's a stable ID (not hash)
                    if STABLE_ID_PATTERN.match(value) and len(value) > 2:
                        return current, value, attr

            current = current.parent
            depth += 1

        return None, None, None

    def _build_path(
        self,
        anchor: Tag,
        target: Tag,
    ) -> tuple[str, int]:
        """Build CSS path from anchor to target.

        Returns:
            Tuple of (CSS path string, depth).
        """
        path_parts = []
        current = target
        depth = 0

        while current and current is not anchor:
            if isinstance(current, Tag):
                # Get tag with distinguishing info
                tag = current.name

                # Add class if available
                classes = current.get('class')
                if classes and isinstance(classes, list):
                    # Use first non-hash class
                    for cls in classes:
                        if not re.match(r'^(css-|sc-|_[a-z0-9]{4,})', cls, re.I):
                            tag = f"{tag}.{cls}"
                            break

                # Add nth-child if needed for disambiguation
                if current.parent:
                    siblings = [
                        s for s in current.parent.children
                        if isinstance(s, Tag) and s.name == current.name
                    ]
                    if len(siblings) > 1:
                        idx = siblings.index(current) + 1
                        tag = f"{tag}:nth-child({idx})"

                path_parts.insert(0, tag)
                depth += 1

            current = current.parent

        return ' > '.join(path_parts), depth

    def _generate_css_selector(
        self,
        element: Tag,
        anchor_id: str | None,
        anchor_path: str,
    ) -> str:
        """Generate optimal CSS selector for element."""
        # If element has ID, use it directly
        el_id = element.get('id')
        if el_id and isinstance(el_id, str) and STABLE_ID_PATTERN.match(el_id):
            return f"#{el_id}"

        # If element has data-testid, use it
        for attr in ['data-testid', 'data-test-id', 'data-cy']:
            value = element.get(attr)
            if value and isinstance(value, str):
                return f"[{attr}=\"{value}\"]"

        # Use anchor + path
        if anchor_id and anchor_path:
            return f"#{anchor_id} {anchor_path}"

        # Fall back to tag + classes
        tag = element.name
        classes = element.get('class')
        if classes and isinstance(classes, list):
            stable_classes = self._filter_classes(classes)
            if stable_classes:
                return f"{tag}.{'.'.join(stable_classes)}"

        return tag

    def _generate_xpath(
        self,
        element: Tag,
        anchor_id: str | None,
        anchor_path: str,  # noqa: ARG002 - reserved for future use
    ) -> str:
        """Generate XPath expression for element."""
        # If element has ID, use it directly
        el_id = element.get('id')
        if el_id and isinstance(el_id, str) and STABLE_ID_PATTERN.match(el_id):
            return f"//*[@id='{el_id}']"

        # If element has data-testid, use it
        for attr in ['data-testid', 'data-test-id', 'data-cy']:
            value = element.get(attr)
            if value and isinstance(value, str):
                return f"//*[@{attr}='{value}']"

        # Use anchor + descendant
        if anchor_id:
            tag = element.name
            return f"//*[@id='{anchor_id}']//{tag}"

        # Fall back to basic XPath
        return f"//{element.name}"


# =============================================================================
# Convenience Functions
# =============================================================================

def extract_context(
    element: Tag,
    include_siblings: bool = True,
    max_siblings: int = 2,
) -> ContextWindow:
    """Extract context window around an element (convenience function).

    Args:
        element: Target element.
        include_siblings: Include sibling elements.
        max_siblings: Maximum siblings on each side.

    Returns:
        ContextWindow with extracted context.
    """
    config = ContextConfig(
        include_siblings=include_siblings,
        max_siblings=max_siblings,
    )
    return ContextExtractor(config).extract(element)


def find_stable_anchor(element: Tag, max_depth: int = 10) -> Optional[str]:
    """Find the ID of the closest stable ancestor.

    Args:
        element: Element to search from.
        max_depth: Maximum depth to search.

    Returns:
        Stable ID string or None.
    """
    extractor = ContextExtractor()
    _, anchor_id, _ = extractor._find_stable_anchor(element, max_depth)
    return anchor_id


def generate_selector(element: Tag) -> str:
    """Generate optimal CSS selector for an element.

    Args:
        element: Target element.

    Returns:
        CSS selector string.
    """
    context = ContextExtractor().extract(element)
    return context.css_selector
