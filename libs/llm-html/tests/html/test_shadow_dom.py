"""Tests for Shadow DOM flattening."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.transformers.shadow_dom import (
    ShadowDOMFlattener,
    FlattenResult,
    FlattenStats,
    flatten_shadow_dom,
    CUSTOM_ELEMENT_PATTERN,
)


class TestCustomElementDetection:
    """Tests for custom element detection."""

    def test_detect_simple_custom_element(self):
        """Detect simple custom element names."""
        assert CUSTOM_ELEMENT_PATTERN.match('my-element')
        assert CUSTOM_ELEMENT_PATTERN.match('custom-button')
        assert CUSTOM_ELEMENT_PATTERN.match('app-header')

    def test_detect_multi_hyphen_custom_element(self):
        """Detect custom elements with multiple hyphens."""
        assert CUSTOM_ELEMENT_PATTERN.match('my-custom-element')
        assert CUSTOM_ELEMENT_PATTERN.match('app-nav-bar-item')

    def test_detect_with_numbers(self):
        """Detect custom elements with numbers."""
        assert CUSTOM_ELEMENT_PATTERN.match('my-element-2')
        assert CUSTOM_ELEMENT_PATTERN.match('v2-button')

    def test_reject_standard_html_tags(self):
        """Reject standard HTML tags."""
        assert not CUSTOM_ELEMENT_PATTERN.match('div')
        assert not CUSTOM_ELEMENT_PATTERN.match('span')
        assert not CUSTOM_ELEMENT_PATTERN.match('button')
        assert not CUSTOM_ELEMENT_PATTERN.match('article')

    def test_reject_without_hyphen(self):
        """Reject element names without hyphens."""
        assert not CUSTOM_ELEMENT_PATTERN.match('myelement')
        assert not CUSTOM_ELEMENT_PATTERN.match('CustomButton')


class TestDeclarativeShadowDOM:
    """Tests for declarative Shadow DOM flattening."""

    def test_flatten_basic_shadow_root(self):
        """Flatten basic declarative shadow DOM."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <style>:host { color: red; }</style>
                <p>Shadow content</p>
            </template>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.had_shadow_dom
        assert result.stats.shadow_roots_found == 1
        assert result.stats.shadow_roots_flattened == 1

        # Shadow content should be visible
        assert soup.find('p', string='Shadow content')

        # Template should be removed
        assert soup.find('template') is None

    def test_flatten_shadowrootmode_attribute(self):
        """Handle newer shadowrootmode attribute."""
        html = '''
        <my-element>
            <template shadowrootmode="open">
                <span>New spec shadow content</span>
            </template>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.had_shadow_dom
        assert soup.find('span', string='New spec shadow content')

    def test_flatten_closed_shadow_root(self):
        """Handle closed shadow roots."""
        html = '''
        <my-element>
            <template shadowroot="closed">
                <p>Closed shadow content</p>
            </template>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.had_shadow_dom
        assert soup.find('p', string='Closed shadow content')

    def test_mark_shadow_host(self):
        """Add markers to shadow hosts."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <p>Content</p>
            </template>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener(mark_boundaries=True)
        flattener.flatten(soup)

        host = soup.find('my-element')
        assert host.get('data-cmdop-shadow-host') == 'true'
        assert host.get('data-cmdop-shadow-mode') == 'open'

    def test_no_mark_when_disabled(self):
        """Don't mark hosts when mark_boundaries=False."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <p>Content</p>
            </template>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener(mark_boundaries=False)
        flattener.flatten(soup)

        host = soup.find('my-element')
        assert host.get('data-cmdop-shadow-host') is None


class TestNestedShadowDOM:
    """Tests for nested Shadow DOM handling."""

    def test_flatten_nested_shadow_roots(self):
        """Flatten nested shadow roots recursively."""
        html = '''
        <outer-element>
            <template shadowroot="open">
                <inner-element>
                    <template shadowroot="open">
                        <p>Deeply nested content</p>
                    </template>
                </inner-element>
            </template>
        </outer-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        # At least 2 shadow roots should be processed
        assert result.stats.shadow_roots_found >= 2
        assert result.stats.shadow_roots_flattened >= 2
        assert result.stats.max_nesting_depth >= 1

        # All content should be visible
        assert soup.find('p', string='Deeply nested content')


class TestSlotResolution:
    """Tests for slot element resolution."""

    def test_flatten_with_light_dom_content(self):
        """Light DOM content is preserved after flattening."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <div class="wrapper">
                    <span>Shadow content</span>
                </div>
            </template>
            <p>Light DOM content</p>
        </my-element>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        # Shadow content should be visible
        assert soup.find('span', string='Shadow content')
        # Light DOM content should be preserved
        assert soup.find('p', string='Light DOM content')
        # Template should be removed
        assert soup.find('template') is None

    def test_slot_in_shadow_dom(self):
        """Slots in shadow DOM are handled."""
        html = '''
        <my-card>
            <template shadowroot="open">
                <header>Header</header>
                <slot></slot>
                <footer>Footer</footer>
            </template>
            <p>Slotted content</p>
        </my-card>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        flattener.flatten(soup)

        # Shadow structure should be visible
        assert soup.find('header', string='Header')
        assert soup.find('footer', string='Footer')
        # Light DOM content should still exist
        assert soup.find('p', string='Slotted content')


class TestCustomElementMarking:
    """Tests for custom element marking."""

    def test_find_custom_elements(self):
        """Find all custom elements in document."""
        html = '''
        <html>
            <body>
                <my-header></my-header>
                <div>
                    <product-card></product-card>
                    <product-card></product-card>
                </div>
                <app-footer></app-footer>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.stats.custom_elements_found == 4

    def test_mark_custom_elements(self):
        """Mark custom elements with data attribute."""
        html = '''
        <my-element></my-element>
        <another-component></another-component>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        marked = flattener.mark_shadow_boundaries(soup)

        assert marked == 2

        my_element = soup.find('my-element')
        assert my_element.get('data-cmdop-custom-element') == 'true'


class TestNoShadowDOM:
    """Tests for HTML without Shadow DOM."""

    def test_no_shadow_dom(self):
        """Handle HTML without any Shadow DOM."""
        html = '''
        <html>
            <body>
                <header>Header</header>
                <main>Content</main>
                <footer>Footer</footer>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert not result.had_shadow_dom
        assert result.stats.shadow_roots_found == 0
        assert result.stats.shadow_roots_flattened == 0

    def test_template_without_shadowroot(self):
        """Ignore regular template elements."""
        html = '''
        <template id="my-template">
            <p>Template content</p>
        </template>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert not result.had_shadow_dom
        # Regular template should remain
        assert soup.find('template', id='my-template')


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_flatten_shadow_dom_function(self):
        """Test flatten_shadow_dom convenience function."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <p>Shadow content</p>
            </template>
        </my-element>
        '''

        result = flatten_shadow_dom(html)

        assert 'Shadow content' in result
        assert '<template' not in result
        assert 'data-cmdop-shadow-host="true"' in result

    def test_flatten_shadow_dom_no_markers(self):
        """Test convenience function without markers."""
        html = '''
        <my-element>
            <template shadowroot="open">
                <p>Content</p>
            </template>
        </my-element>
        '''

        result = flatten_shadow_dom(html, mark_boundaries=False)

        assert 'Content' in result
        assert 'data-cmdop-shadow-host' not in result


class TestFlattenStats:
    """Tests for FlattenStats dataclass."""

    def test_default_values(self):
        """Test default values."""
        stats = FlattenStats()

        assert stats.shadow_roots_found == 0
        assert stats.shadow_roots_flattened == 0
        assert stats.slots_resolved == 0
        assert stats.custom_elements_found == 0
        assert stats.max_nesting_depth == 0


class TestRealWorldExamples:
    """Tests with real-world-like examples."""

    def test_web_component_card(self):
        """Test web component card pattern."""
        html = '''
        <product-card>
            <template shadowroot="open">
                <style>
                    :host { display: block; border: 1px solid #ccc; }
                    .title { font-weight: bold; }
                    .price { color: green; }
                </style>
                <div class="card">
                    <h3 class="title">Product Title</h3>
                    <p class="price">$99.99</p>
                    <p class="description">Product description</p>
                </div>
            </template>
        </product-card>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.had_shadow_dom
        assert result.stats.shadow_roots_flattened == 1

        # Shadow content should be accessible
        assert soup.find('h3', class_='title')
        assert soup.find('p', class_='price')
        assert soup.find('p', class_='description')

        # Template should be removed
        assert soup.find('template') is None

    def test_material_design_button(self):
        """Test Material Design-like button component."""
        html = '''
        <md-button>
            <template shadowroot="open">
                <button class="md-button__native">
                    <span class="md-button__label">Click me</span>
                    <span class="md-button__ripple"></span>
                </button>
            </template>
        </md-button>
        '''

        soup = BeautifulSoup(html, 'lxml')
        flattener = ShadowDOMFlattener()
        result = flattener.flatten(soup)

        assert result.had_shadow_dom

        # Internal structure should be flattened
        assert soup.find('button', class_='md-button__native')
        assert soup.find('span', class_='md-button__label')
        assert soup.find('span', class_='md-button__ripple')
