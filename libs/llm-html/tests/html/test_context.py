"""Tests for context window extraction."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.extractors.context import (
    ContextExtractor,
    ContextWindow,
    ContextConfig,
    extract_context,
    find_stable_anchor,
    generate_selector,
)


class TestContextExtractor:
    """Tests for ContextExtractor class."""

    def test_extract_basic(self):
        """Extract context from basic element."""
        html = '''
        <div id="container">
            <p>Before</p>
            <button class="primary-btn">Click Me</button>
            <p>After</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.target_tag == 'button'
        assert 'Click Me' in context.target
        assert context.parent_tag == 'div'
        assert context.anchor_id == 'container'

    def test_extract_with_siblings(self):
        """Extract siblings around target."""
        html = '''
        <ul id="list">
            <li>Item 1</li>
            <li>Item 2</li>
            <li id="target">Target</li>
            <li>Item 4</li>
            <li>Item 5</li>
        </ul>
        '''
        soup = BeautifulSoup(html, 'lxml')
        target = soup.find('li', id='target')

        config = ContextConfig(max_siblings=2)
        extractor = ContextExtractor(config)
        context = extractor.extract(target)

        assert len(context.prev_siblings) == 2
        assert len(context.next_siblings) == 2
        assert 'Item 2' in context.prev_siblings[0]
        assert 'Item 4' in context.next_siblings[0]

    def test_extract_without_siblings(self):
        """Extract without siblings when disabled."""
        html = '''
        <ul id="list">
            <li>Item 1</li>
            <li id="target">Target</li>
            <li>Item 3</li>
        </ul>
        '''
        soup = BeautifulSoup(html, 'lxml')
        target = soup.find('li', id='target')

        config = ContextConfig(include_siblings=False)
        extractor = ContextExtractor(config)
        context = extractor.extract(target)

        assert len(context.prev_siblings) == 0
        assert len(context.next_siblings) == 0

    def test_find_stable_anchor(self):
        """Find stable anchor in ancestry."""
        html = '''
        <div id="app">
            <main>
                <section>
                    <div>
                        <button>Nested Button</button>
                    </div>
                </section>
            </main>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.anchor_id == 'app'
        assert context.depth > 0

    def test_find_data_testid_anchor(self):
        """Find data-testid as stable anchor."""
        html = '''
        <div data-testid="product-card">
            <h3>Product</h3>
            <button>Add to Cart</button>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.anchor_id == 'product-card'

    def test_no_stable_anchor(self):
        """Handle case with no stable anchor."""
        html = '''
        <div>
            <span class="css-abc123">
                <button>Click</button>
            </span>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.anchor_id is None
        assert context.anchor_path == ""

    def test_generate_css_selector_with_id(self):
        """Generate selector for element with ID."""
        html = '<button id="submit-btn">Submit</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.css_selector == '#submit-btn'

    def test_generate_css_selector_with_testid(self):
        """Generate selector for element with data-testid."""
        html = '<button data-testid="login-button">Login</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.css_selector == '[data-testid="login-button"]'

    def test_generate_xpath(self):
        """Generate XPath for element."""
        html = '<button id="submit-btn">Submit</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.xpath == "//*[@id='submit-btn']"

    def test_minimize_html(self):
        """Minimize HTML output."""
        html = '''
        <div class="product-card css-abc123 _hash123">
            <h3 class="title">Product Name</h3>
            <p class="description">Long description here...</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div', class_='product-card')

        config = ContextConfig(minimize_html=True)
        extractor = ContextExtractor(config)
        context = extractor.extract(div)

        # Should not contain hash classes
        assert 'css-abc123' not in context.target
        # Should contain semantic class
        assert 'product-card' in context.target

    def test_extract_from_selector(self):
        """Extract context for multiple elements."""
        html = '''
        <div id="products">
            <div class="product">Product 1</div>
            <div class="product">Product 2</div>
            <div class="product">Product 3</div>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')

        extractor = ContextExtractor()
        contexts = extractor.extract_from_selector(soup, '.product')

        assert len(contexts) == 3
        for ctx in contexts:
            assert ctx.target_tag == 'div'
            assert ctx.anchor_id == 'products'


class TestContextConfig:
    """Tests for ContextConfig."""

    def test_default_values(self):
        """Test default configuration."""
        config = ContextConfig()

        assert config.include_parent is True
        assert config.include_siblings is True
        assert config.max_siblings == 2
        assert config.find_stable_anchor is True
        assert config.max_anchor_depth == 10

    def test_custom_values(self):
        """Test custom configuration."""
        config = ContextConfig(
            include_parent=False,
            max_siblings=5,
            max_anchor_depth=5,
        )

        assert config.include_parent is False
        assert config.max_siblings == 5
        assert config.max_anchor_depth == 5


class TestContextWindow:
    """Tests for ContextWindow dataclass."""

    def test_context_window_attributes(self):
        """Test ContextWindow attributes."""
        window = ContextWindow(
            target='<button>Click</button>',
            target_tag='button',
            parent='<div>[1 children]</div>',
            parent_tag='div',
            prev_siblings=['<p>Before</p>'],
            next_siblings=['<p>After</p>'],
            anchor_id='container',
            anchor_tag='div',
            anchor_path='button',
            depth=1,
            css_selector='#container button',
            xpath="//*[@id='container']//button",
        )

        assert window.target_tag == 'button'
        assert window.anchor_id == 'container'
        assert window.depth == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_extract_context(self):
        """Test extract_context function."""
        html = '''
        <div id="form">
            <input type="text" placeholder="Name">
            <button>Submit</button>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        context = extract_context(button)

        assert context.target_tag == 'button'
        assert context.anchor_id == 'form'

    def test_find_stable_anchor_function(self):
        """Test find_stable_anchor function."""
        html = '''
        <div id="app">
            <section>
                <button>Click</button>
            </section>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        anchor = find_stable_anchor(button)
        assert anchor == 'app'

    def test_generate_selector_function(self):
        """Test generate_selector function."""
        html = '<button data-testid="save-btn">Save</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        selector = generate_selector(button)
        assert selector == '[data-testid="save-btn"]'


class TestEdgeCases:
    """Tests for edge cases."""

    def test_deeply_nested_element(self):
        """Handle deeply nested elements."""
        html = '''
        <div id="root">
            <div>
                <div>
                    <div>
                        <div>
                            <div>
                                <button>Deep</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        assert context.anchor_id == 'root'
        assert context.depth > 3

    def test_element_at_document_root(self):
        """Handle element near document root."""
        html = '<button>Root Button</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        # Should still work without error
        assert context.target_tag == 'button'

    def test_element_with_no_parent(self):
        """Handle element without meaningful parent."""
        html = '<button>Solo</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        config = ContextConfig(include_parent=True)
        extractor = ContextExtractor(config)
        context = extractor.extract(button)

        # Parent might be body or html
        assert context.target_tag == 'button'

    def test_element_with_long_text(self):
        """Handle element with very long text content."""
        long_text = "Lorem ipsum " * 100
        html = f'<p id="test">{long_text}</p>'
        soup = BeautifulSoup(html, 'lxml')
        p = soup.find('p')

        config = ContextConfig(minimize_html=True)
        extractor = ContextExtractor(config)
        context = extractor.extract(p)

        # Text should be truncated
        assert len(context.target) < len(long_text)
        assert '...' in context.target

    def test_sibling_order_preserved(self):
        """Siblings should be in correct order."""
        html = '''
        <ul id="list">
            <li>A</li>
            <li>B</li>
            <li id="target">Target</li>
            <li>D</li>
            <li>E</li>
        </ul>
        '''
        soup = BeautifulSoup(html, 'lxml')
        target = soup.find('li', id='target')

        extractor = ContextExtractor()
        context = extractor.extract(target)

        # Previous sibling should be B (closest first)
        assert 'B' in context.prev_siblings[0]
        # Next sibling should be D (closest first)
        assert 'D' in context.next_siblings[0]


class TestRealWorldScenarios:
    """Tests with real-world-like scenarios."""

    def test_ecommerce_product_card(self):
        """E-commerce product card scenario."""
        html = '''
        <div id="product-listing">
            <div class="product-card" data-testid="product-1">
                <img src="product.jpg" alt="Product">
                <h3 class="product-title">Amazing Product</h3>
                <span class="price">$99.99</span>
                <button class="add-to-cart">Add to Cart</button>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        extractor = ContextExtractor()
        context = extractor.extract(button)

        # Should find product card as anchor
        assert context.anchor_id in ['product-1', 'product-listing']
        assert context.css_selector is not None

    def test_navigation_menu(self):
        """Navigation menu scenario."""
        html = '''
        <nav id="main-nav" role="navigation">
            <a href="/" class="nav-link">Home</a>
            <a href="/products" class="nav-link active">Products</a>
            <a href="/about" class="nav-link">About</a>
        </nav>
        '''
        soup = BeautifulSoup(html, 'lxml')
        active_link = soup.find('a', class_='active')

        extractor = ContextExtractor()
        context = extractor.extract(active_link)

        assert context.anchor_id == 'main-nav'
        assert len(context.prev_siblings) >= 1
        assert len(context.next_siblings) >= 1

    def test_form_input(self):
        """Form input scenario."""
        html = '''
        <form id="login-form" action="/login" method="post">
            <label for="email">Email</label>
            <input type="email" id="email" name="email" placeholder="Enter email">
            <label for="password">Password</label>
            <input type="password" id="password" name="password">
            <button type="submit">Login</button>
        </form>
        '''
        soup = BeautifulSoup(html, 'lxml')
        email_input = soup.find('input', id='email')

        extractor = ContextExtractor()
        context = extractor.extract(email_input)

        assert context.css_selector == '#email'
        assert context.anchor_id == 'login-form'

    def test_table_cell(self):
        """Table cell scenario."""
        html = '''
        <table id="data-table">
            <thead>
                <tr><th>Name</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>Row 1</td>
                    <td data-testid="value-1">100</td>
                </tr>
            </tbody>
        </table>
        '''
        soup = BeautifulSoup(html, 'lxml')
        cell = soup.find('td', attrs={'data-testid': 'value-1'})

        extractor = ContextExtractor()
        context = extractor.extract(cell)

        assert context.css_selector == '[data-testid="value-1"]'
