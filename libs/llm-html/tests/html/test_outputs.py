"""Tests for output format exporters."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.outputs import (
    AOMYAMLExporter,
    AOMConfig,
    to_aom_yaml,
    MarkdownExporter,
    MarkdownConfig,
    to_markdown,
    XTreeExporter,
    XTreeConfig,
    to_xtree,
)


class TestAOMYAMLExporter:
    """Tests for AOM YAML exporter."""

    def test_basic_export(self):
        """Export basic HTML to AOM YAML."""
        html = '''
        <nav>
            <a href="/">Home</a>
            <a href="/products">Products</a>
        </nav>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'navigation' in result
        assert 'link' in result
        assert 'Home' in result
        assert 'Products' in result

    def test_heading_levels(self):
        """Export headings with levels."""
        html = '''
        <h1>Main Title</h1>
        <h2>Section</h2>
        <h3>Subsection</h3>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'heading "Main Title"' in result
        assert 'level=1' in result
        assert 'level=2' in result

    def test_list_structure(self):
        """Export list structure."""
        html = '''
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'list' in result
        assert 'listitem' in result

    def test_button_role(self):
        """Export button with correct role."""
        html = '<button>Click Me</button>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'button "Click Me"' in result

    def test_input_roles(self):
        """Export inputs with appropriate roles."""
        html = '''
        <input type="text" placeholder="Name">
        <input type="checkbox">
        <input type="submit" value="Submit">
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'textbox' in result
        assert 'checkbox' in result
        assert 'button' in result

    def test_explicit_role_override(self):
        """Explicit role overrides implicit."""
        html = '<div role="button">Fake Button</div>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'button "Fake Button"' in result

    def test_aria_label(self):
        """Use aria-label for accessible name."""
        html = '<button aria-label="Close dialog">X</button>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = AOMYAMLExporter()
        result = exporter.export(soup)

        assert 'Close dialog' in result

    def test_disabled_state(self):
        """Include disabled attribute."""
        html = '<button disabled>Disabled Button</button>'
        soup = BeautifulSoup(html, 'lxml')
        config = AOMConfig(include_attributes=True)
        exporter = AOMYAMLExporter(config)
        result = exporter.export(soup)

        assert 'disabled=true' in result

    def test_skip_empty_elements(self):
        """Skip empty elements when configured."""
        html = '<nav><a href="#">Link</a></nav>'
        soup = BeautifulSoup(html, 'lxml')
        config = AOMConfig(skip_empty=True)
        exporter = AOMYAMLExporter(config)
        result = exporter.export(soup)

        assert 'link' in result
        assert 'Link' in result

    def test_convenience_function(self):
        """Test to_aom_yaml convenience function."""
        html = '<button>Test</button>'
        result = to_aom_yaml(html)

        assert 'button "Test"' in result


class TestMarkdownExporter:
    """Tests for Markdown exporter."""

    def test_basic_export(self):
        """Export basic HTML to Markdown."""
        html = '''
        <h1>Title</h1>
        <p>This is a paragraph.</p>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '# Title' in result
        assert 'This is a paragraph.' in result

    def test_heading_levels(self):
        """Export different heading levels."""
        html = '''
        <h1>H1</h1>
        <h2>H2</h2>
        <h3>H3</h3>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '# H1' in result
        assert '## H2' in result
        assert '### H3' in result

    def test_unordered_list(self):
        """Export unordered list."""
        html = '''
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '- Item 1' in result
        assert '- Item 2' in result

    def test_ordered_list(self):
        """Export ordered list."""
        html = '''
        <ol>
            <li>First</li>
            <li>Second</li>
        </ol>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '1. First' in result
        assert '2. Second' in result

    def test_link_export(self):
        """Export links."""
        html = '<a href="https://example.com">Example</a>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '[Example](https://example.com)' in result

    def test_skip_javascript_links(self):
        """Skip javascript: links."""
        html = '<a href="javascript:void(0)">Click</a>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert 'Click' in result
        assert 'javascript' not in result

    def test_strong_emphasis(self):
        """Export strong and emphasis."""
        html = '<p><strong>Bold</strong> and <em>italic</em></p>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '**Bold**' in result
        assert '*italic*' in result

    def test_table_export(self):
        """Export table."""
        html = '''
        <table>
            <thead>
                <tr><th>Name</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr><td>A</td><td>1</td></tr>
                <tr><td>B</td><td>2</td></tr>
            </tbody>
        </table>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '| Name | Value |' in result
        assert '| --- | --- |' in result
        assert '| A | 1 |' in result

    def test_blockquote(self):
        """Export blockquote."""
        html = '<blockquote>Quote text</blockquote>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '> Quote text' in result

    def test_code_block(self):
        """Export code block."""
        html = '<pre><code>print("hello")</code></pre>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '```' in result
        assert 'print("hello")' in result

    def test_inline_code(self):
        """Export inline code."""
        html = '<p>Use <code>print()</code> to output</p>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '`print()`' in result

    def test_image_included(self):
        """Include images when configured."""
        html = '<img src="image.jpg" alt="Test Image">'
        soup = BeautifulSoup(html, 'lxml')
        config = MarkdownConfig(include_images=True)
        exporter = MarkdownExporter(config)
        result = exporter.export(soup)

        assert '![Test Image](image.jpg)' in result

    def test_image_excluded(self):
        """Exclude images by default."""
        html = '<img src="image.jpg" alt="Test Image">'
        soup = BeautifulSoup(html, 'lxml')
        exporter = MarkdownExporter()
        result = exporter.export(soup)

        assert '![' not in result

    def test_convenience_function(self):
        """Test to_markdown convenience function."""
        html = '<h1>Test</h1>'
        result = to_markdown(html)

        assert '# Test' in result


class TestXTreeExporter:
    """Tests for XTree exporter."""

    def test_basic_export(self):
        """Export basic HTML to XTree."""
        html = '''
        <div id="container">
            <h1>Title</h1>
            <p>Paragraph</p>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        exporter = XTreeExporter()
        result = exporter.export(soup)

        assert 'ROOT' in result
        assert 'div#container' in result
        assert 'h1' in result
        assert 'Title' in result

    def test_tree_characters(self):
        """Use correct tree characters."""
        html = '''
        <div>
            <span>A</span>
            <span>B</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(use_unicode=True)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        assert '├─' in result or '└─' in result

    def test_ascii_mode(self):
        """Use ASCII characters when configured."""
        html = '''
        <div>
            <span>A</span>
            <span>B</span>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(use_unicode=False)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        assert '+-' in result or '\\-' in result

    def test_class_display(self):
        """Display classes in output."""
        html = '<div class="product-card">Product</div>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = XTreeExporter()
        result = exporter.export(soup)

        assert 'div.product-card' in result

    def test_filter_hash_classes(self):
        """Filter out hash classes."""
        html = '<div class="product css-abc123 _hash456">Product</div>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = XTreeExporter()
        result = exporter.export(soup)

        assert 'product' in result
        assert 'css-abc123' not in result
        assert '_hash456' not in result

    def test_max_depth(self):
        """Respect max depth setting."""
        html = '''
        <div>
            <div>
                <div>
                    <div>
                        <div>Deep</div>
                    </div>
                </div>
            </div>
        </div>
        '''
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(max_depth=2)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        # Should not show deepest levels
        lines = result.split('\n')
        assert len(lines) < 10

    def test_max_children(self):
        """Limit children shown."""
        items = '\n'.join([f'<li>Item {i}</li>' for i in range(20)])
        html = f'<ul>{items}</ul>'
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(max_children=5)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        # Should show truncation indicator
        assert '…' in result or '...' in result
        assert 'more' in result

    def test_text_content(self):
        """Show text content with arrow."""
        html = '<button>Click Me</button>'
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(show_text=True)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        assert '→' in result or '->' in result
        assert 'Click Me' in result

    def test_text_truncation(self):
        """Truncate long text."""
        long_text = "A" * 200
        html = f'<p>{long_text}</p>'
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(max_text_length=50)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        assert '...' in result
        assert long_text not in result

    def test_attributes(self):
        """Show relevant attributes."""
        html = '<input type="checkbox" disabled value="on">'
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(show_attributes=True, filter_empty=False)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        assert 'input' in result
        assert 'type=checkbox' in result
        assert 'disabled' in result

    def test_data_testid(self):
        """Show data-testid attribute."""
        html = '<button data-testid="submit-btn">Submit</button>'
        soup = BeautifulSoup(html, 'lxml')
        exporter = XTreeExporter()
        result = exporter.export(soup)

        assert 'testid=submit-btn' in result

    def test_filter_empty(self):
        """Filter empty elements."""
        html = '<div><span></span><p>Content</p></div>'
        soup = BeautifulSoup(html, 'lxml')
        config = XTreeConfig(filter_empty=True)
        exporter = XTreeExporter(config)
        result = exporter.export(soup)

        # Empty span should be filtered
        lines = [l for l in result.split('\n') if 'span' in l.lower()]
        assert len(lines) == 0

    def test_convenience_function(self):
        """Test to_xtree convenience function."""
        html = '<div id="test">Content</div>'
        result = to_xtree(html)

        assert 'ROOT' in result
        assert 'div#test' in result


class TestRealWorldScenarios:
    """Tests with real-world-like HTML."""

    def test_ecommerce_aom(self):
        """E-commerce page to AOM YAML."""
        html = '''
        <main>
            <h1>Products</h1>
            <ul class="product-list">
                <li class="product">
                    <h3>Product 1</h3>
                    <span class="price">$99.99</span>
                    <button>Add to Cart</button>
                </li>
            </ul>
        </main>
        '''
        result = to_aom_yaml(html)

        assert 'main' in result
        assert 'heading' in result
        assert 'button' in result

    def test_blog_markdown(self):
        """Blog post to Markdown."""
        html = '''
        <article>
            <h1>Blog Title</h1>
            <p>Published <time>2024-01-15</time></p>
            <p>This is the <strong>introduction</strong> paragraph.</p>
            <h2>Section 1</h2>
            <p>More content here.</p>
            <a href="/next">Next Post</a>
        </article>
        '''
        result = to_markdown(html)

        assert '# Blog Title' in result
        assert '## Section 1' in result
        assert '**introduction**' in result
        assert '[Next Post](/next)' in result

    def test_form_xtree(self):
        """Form to XTree."""
        html = '''
        <form id="login-form">
            <label for="email">Email</label>
            <button type="submit">Login</button>
        </form>
        '''
        result = to_xtree(html)

        assert 'form#login-form' in result
        assert 'label' in result
        assert 'button' in result
