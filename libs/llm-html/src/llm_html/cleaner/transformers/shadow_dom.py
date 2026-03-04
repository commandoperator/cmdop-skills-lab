"""Shadow DOM flattening for LLM visibility.

Web Components with Shadow DOM create encapsulation boundaries that
standard global selectors cannot pierce. This module flattens declarative
shadow DOM so LLMs can see the full content.

Key patterns handled:
- Declarative Shadow DOM: <template shadowroot="open">...</template>
- Slots with fallback content: <slot name="foo">fallback</slot>
- Nested shadow roots (recursive flattening)

Note: For browser-rendered HTML (e.g., from Playwright/Puppeteer),
shadow roots are typically already expanded into the DOM. This module
is primarily for handling raw HTML with declarative shadow DOM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString


@dataclass
class FlattenStats:
    """Statistics from Shadow DOM flattening."""

    shadow_roots_found: int = 0
    """Number of declarative shadow roots found."""

    shadow_roots_flattened: int = 0
    """Number successfully flattened."""

    slots_resolved: int = 0
    """Number of slot elements resolved."""

    custom_elements_found: int = 0
    """Number of custom elements (with hyphens in tag name)."""

    max_nesting_depth: int = 0
    """Maximum shadow DOM nesting depth encountered."""


@dataclass
class FlattenResult:
    """Result of Shadow DOM flattening."""

    soup: BeautifulSoup
    """The flattened BeautifulSoup object."""

    stats: FlattenStats = field(default_factory=FlattenStats)
    """Flattening statistics."""

    had_shadow_dom: bool = False
    """Whether any shadow DOM was found and processed."""


# Pattern for custom element tags (contain at least one hyphen)
CUSTOM_ELEMENT_PATTERN = re.compile(r'^[a-z][a-z0-9]*-[a-z0-9-]+$', re.IGNORECASE)


class ShadowDOMFlattener:
    """Recursively flatten Shadow DOM for LLM visibility.

    This class handles declarative shadow DOM and makes shadow content
    visible to LLMs by flattening the shadow trees into the light DOM.

    Example:
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        if result.had_shadow_dom:
            print(f"Flattened {result.stats.shadow_roots_flattened} shadow roots")
    """

    def __init__(
        self,
        mark_boundaries: bool = True,
        preserve_slots: bool = False,
        remove_template_tags: bool = True,
    ):
        """Initialize the flattener.

        Args:
            mark_boundaries: Add data-cmdop-shadow-host markers for debugging.
            preserve_slots: Keep slot elements (resolved) in output.
            remove_template_tags: Remove template tags after flattening.
        """
        self.mark_boundaries = mark_boundaries
        self.preserve_slots = preserve_slots
        self.remove_template_tags = remove_template_tags

    def flatten(self, soup: BeautifulSoup) -> FlattenResult:
        """Flatten all shadow DOM in the document.

        Args:
            soup: BeautifulSoup document to process.

        Returns:
            FlattenResult with flattened soup and statistics.
        """
        stats = FlattenStats()

        # Find custom elements (potential shadow hosts)
        custom_elements = self._find_custom_elements(soup)
        stats.custom_elements_found = len(custom_elements)

        # Find and process all declarative shadow roots
        self._flatten_recursive(soup, stats, depth=0)

        # Note: Slot resolution is disabled as it requires complex DOM tracking
        # The slots are left in place after flattening
        # stats.slots_resolved = self._resolve_slots(soup)

        had_shadow = stats.shadow_roots_found > 0

        return FlattenResult(
            soup=soup,
            stats=stats,
            had_shadow_dom=had_shadow,
        )

    def _find_custom_elements(self, soup: BeautifulSoup) -> List[Tag]:
        """Find all custom elements (tags with hyphens).

        Custom elements often use Shadow DOM for encapsulation.
        """
        custom_elements = []

        for tag in soup.find_all(True):  # Find all tags
            if isinstance(tag, Tag) and CUSTOM_ELEMENT_PATTERN.match(tag.name):
                custom_elements.append(tag)

        return custom_elements

    def _flatten_recursive(
        self,
        element: BeautifulSoup | Tag,
        stats: FlattenStats,
        depth: int = 0,
    ) -> None:
        """Recursively find and flatten shadow roots.

        Handles declarative shadow DOM:
        <template shadowroot="open">...</template>
        <template shadowrootmode="open">...</template> (newer spec)
        """
        if depth > stats.max_nesting_depth:
            stats.max_nesting_depth = depth

        # Find templates with shadowroot or shadowrootmode attribute
        shadow_templates = []
        for template in element.find_all('template'):
            if isinstance(template, Tag):
                if template.get('shadowroot') in ('open', 'closed'):
                    shadow_templates.append(template)
                elif template.get('shadowrootmode') in ('open', 'closed'):
                    shadow_templates.append(template)

        for template in shadow_templates:
            stats.shadow_roots_found += 1

            # Get the shadow host (parent element)
            host = template.parent

            if host and isinstance(host, Tag):
                # Mark the host for debugging
                if self.mark_boundaries:
                    host['data-cmdop-shadow-host'] = 'true'
                    shadow_type = template.get('shadowroot') or template.get('shadowrootmode')
                    host['data-cmdop-shadow-mode'] = shadow_type

                # Extract shadow content
                shadow_content = list(template.children)

                # Insert shadow content into host (before template)
                for child in reversed(shadow_content):
                    if isinstance(child, (Tag, NavigableString)):
                        # Clone the content
                        cloned = child.extract() if isinstance(child, NavigableString) else child
                        template.insert_before(cloned)

                # Remove the template tag
                if self.remove_template_tags:
                    template.decompose()

                stats.shadow_roots_flattened += 1

                # Recursively process nested shadow roots
                self._flatten_recursive(host, stats, depth + 1)

    def _resolve_slots(self, soup: BeautifulSoup) -> int:
        """Resolve slot elements with their slotted content.

        Slots in flattened shadow DOM should be resolved to show
        the actual slotted content or fallback.

        Returns:
            Number of slots resolved.
        """
        resolved_count = 0

        # Find all slot elements (make a copy to avoid modification during iteration)
        slots = list(soup.find_all('slot'))

        for slot in slots:
            if not isinstance(slot, Tag):
                continue

            # Check if slot is still in the document (might have been removed)
            if not slot.parent:
                continue

            slot_name = slot.get('name', '')
            host = self._find_shadow_host(slot)

            slotted_content = []

            if host:
                # Find slotted content in the host's light DOM
                if slot_name:
                    # Named slot: find elements with slot="name"
                    slotted_content = list(host.find_all(attrs={'slot': slot_name}))
                else:
                    # Default slot: find elements without slot attribute
                    # that are direct children of the host
                    slotted_content = [
                        child for child in list(host.children)
                        if isinstance(child, Tag) and not child.get('slot')
                    ]

            # Remove slot element (keep fallback if no slotted content)
            if not self.preserve_slots:
                if slotted_content:
                    # Move slotted content to where slot was
                    for content in slotted_content:
                        if isinstance(content, Tag) and content.parent:
                            slot.insert_before(content.extract())
                else:
                    # Keep fallback content (move it out of slot)
                    for child in list(slot.children):
                        slot.insert_before(child.extract())
                slot.decompose()
                resolved_count += 1
            else:
                # Just count, keep slot in place
                resolved_count += 1

        return resolved_count

    def _find_shadow_host(self, element: Tag) -> Optional[Tag]:
        """Find the shadow host ancestor of an element.

        Looks for parent with data-cmdop-shadow-host marker.
        """
        parent = element.parent
        while parent:
            if isinstance(parent, Tag) and parent.get('data-cmdop-shadow-host'):
                return parent
            parent = parent.parent
        return None

    def mark_shadow_boundaries(self, soup: BeautifulSoup) -> int:
        """Add data-cmdop-shadow-host markers to custom elements.

        This is useful for identifying potential shadow hosts
        even when the shadow content isn't available.

        Returns:
            Number of elements marked.
        """
        marked = 0
        custom_elements = self._find_custom_elements(soup)

        for element in custom_elements:
            element['data-cmdop-custom-element'] = 'true'
            marked += 1

        return marked


# =============================================================================
# Convenience Function
# =============================================================================

def flatten_shadow_dom(
    html: str,
    mark_boundaries: bool = True,
) -> str:
    """Flatten Shadow DOM in HTML string (convenience function).

    Args:
        html: Raw HTML string with potential shadow DOM.
        mark_boundaries: Add markers to shadow hosts.

    Returns:
        HTML string with shadow DOM flattened.
    """
    soup = BeautifulSoup(html, 'lxml')
    flattener = ShadowDOMFlattener(mark_boundaries=mark_boundaries)
    result = flattener.flatten(soup)
    return str(result.soup)
