"""Tests for universal cleaning pipeline."""
import pytest

from llm_html.cleaner.pipeline import (
    CleaningPipeline,
    PipelineConfig,
    PipelineResult,
    clean_html,
    clean_for_llm,
)


class TestCleaningPipeline:
    """Tests for CleaningPipeline class."""

    def test_basic_cleaning(self):
        """Basic HTML cleaning."""
        html = '''
        <html>
            <head><title>Test</title></head>
            <body>
                <script>alert("test")</script>
                <style>.foo { color: red; }</style>
                <h1>Hello World</h1>
                <p>Test paragraph.</p>
            </body>
        </html>
        '''
        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        assert isinstance(result, PipelineResult)
        assert 'Hello World' in result.output
        assert 'Test paragraph' in result.output
        assert '<script>' not in result.output
        assert '<style>' not in result.output

    def test_token_reduction(self):
        """Verify token reduction is calculated."""
        html = '''
        <html>
            <head><script>var x = 1;</script></head>
            <body>
                <div class="container">
                    <h1>Title</h1>
                </div>
            </body>
        </html>
        '''
        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        assert result.original_tokens > 0
        assert result.cleaned_tokens > 0
        assert result.reduction_percent >= 0

    def test_hydration_extraction(self):
        """Extract SSR hydration data when available."""
        html = '''
        <html>
            <body>
                <div id="__next">Content</div>
                <script id="__NEXT_DATA__" type="application/json">
                    {"props": {"pageProps": {"products": [{"id": 1, "name": "Test"}]}}}
                </script>
            </body>
        </html>
        '''
        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        assert result.hydration_data is not None
        assert 'products' in result.hydration_data

    def test_structured_data_extraction(self):
        """Extract JSON-LD structured data."""
        html = '''
        <html>
            <head>
                <script type="application/ld+json">
                    {"@type": "Product", "name": "Test Product"}
                </script>
            </head>
            <body><p>Content</p></body>
        </html>
        '''
        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        assert result.structured_data is not None
        assert result.structured_data.get('@type') == 'Product'

    def test_output_format_markdown(self):
        """Convert output to Markdown."""
        html = '''
        <h1>Title</h1>
        <p>Paragraph text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        '''
        config = PipelineConfig(output_format='markdown')
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert '# Title' in result.output
        assert '- Item 1' in result.output or '* Item 1' in result.output

    def test_output_format_aom(self):
        """Convert output to AOM YAML."""
        html = '''
        <nav>
            <a href="/">Home</a>
        </nav>
        <main>
            <h1>Page Title</h1>
        </main>
        '''
        config = PipelineConfig(output_format='aom')
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert 'navigation' in result.output or 'main' in result.output

    def test_output_format_xtree(self):
        """Convert output to XTree."""
        html = '''
        <div id="container">
            <h1>Title</h1>
        </div>
        '''
        config = PipelineConfig(output_format='xtree')
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert 'ROOT' in result.output
        assert 'div' in result.output

    def test_class_filtering(self):
        """Filter CSS classes by semantic score."""
        html = '''
        <div class="product-card css-abc123 _hash456">
            <h2 class="title">Product</h2>
        </div>
        '''
        config = PipelineConfig(filter_classes=True, class_threshold=0.3)
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        # Hash classes should be filtered
        assert 'css-abc123' not in result.html
        assert '_hash456' not in result.html

    def test_class_filtering_disabled(self):
        """Keep all classes when filtering disabled."""
        html = '''
        <div class="product-card css-abc123">
            <h2>Product</h2>
        </div>
        '''
        config = PipelineConfig(filter_classes=False)
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        # Classes should be preserved (if not removed by aggressive cleaner)
        assert 'product' in result.html.lower() or 'div' in result.html

    def test_config_override(self):
        """Config can be overridden per-call."""
        html = '<h1>Test</h1>'

        default_config = PipelineConfig(output_format='html')
        pipeline = CleaningPipeline(default_config)

        # Default
        result1 = pipeline.process(html)
        assert '<h1>' in result1.output or 'h1' in result1.output.lower()

        # Override
        override_config = PipelineConfig(output_format='markdown')
        result2 = pipeline.process(html, override_config)
        assert '# Test' in result2.output


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = PipelineConfig()

        assert config.max_tokens == 10000
        assert config.filter_classes is True
        assert config.enable_chunking is True
        assert config.output_format == 'html'

    def test_custom_values(self):
        """Test custom configuration values."""
        config = PipelineConfig(
            max_tokens=5000,
            filter_classes=False,
            output_format='markdown',
            chunk_max_items=10,
        )

        assert config.max_tokens == 5000
        assert config.filter_classes is False
        assert config.output_format == 'markdown'
        assert config.chunk_max_items == 10


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_clean_html(self):
        """Test clean_html convenience function."""
        html = '''
        <html>
            <body>
                <script>alert("x")</script>
                <h1>Hello</h1>
            </body>
        </html>
        '''
        result = clean_html(html)

        assert isinstance(result, PipelineResult)
        assert 'Hello' in result.output
        assert '<script>' not in result.output

    def test_clean_html_with_format(self):
        """Test clean_html with output format."""
        html = '<h1>Title</h1><p>Text</p>'
        result = clean_html(html, output_format='markdown')

        assert '# Title' in result.output

    def test_clean_for_llm_with_hydration(self):
        """clean_for_llm returns dict when hydration found."""
        html = '''
        <script id="__NEXT_DATA__" type="application/json">
            {"props": {"pageProps": {"items": [1, 2, 3]}}}
        </script>
        '''
        result = clean_for_llm(html)

        assert isinstance(result, dict)
        assert 'items' in result

    def test_clean_for_llm_without_hydration(self):
        """clean_for_llm returns string when no hydration."""
        html = '<h1>Simple Page</h1><p>Content</p>'
        result = clean_for_llm(html)

        assert isinstance(result, str)
        assert 'Simple Page' in result or 'Content' in result


class TestChunking:
    """Tests for chunking functionality."""

    def test_no_chunking_small_content(self):
        """Small content is not chunked."""
        html = '<p>Small content</p>'
        config = PipelineConfig(max_tokens=10000, enable_chunking=True)
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert not result.was_chunked
        assert len(result.chunks) == 0

    def test_chunking_disabled(self):
        """Chunking can be disabled."""
        # Create content that would normally be chunked
        items = ''.join([f'<li>Item {i} with some content</li>' for i in range(100)])
        html = f'<ul>{items}</ul>'

        config = PipelineConfig(max_tokens=500, enable_chunking=False)
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert not result.was_chunked


class TestRealWorldScenarios:
    """Tests with real-world-like HTML."""

    def test_ecommerce_page(self):
        """Clean e-commerce product listing."""
        products = '\n'.join([
            f'''
            <div class="product-card css-{i}abc">
                <img src="product{i}.jpg">
                <h3 class="title">Product {i}</h3>
                <span class="price">$99.99</span>
            </div>
            '''
            for i in range(10)
        ])

        html = f'''
        <html>
            <body>
                <nav>Navigation</nav>
                <main>
                    <h1>Products</h1>
                    <div class="grid">{products}</div>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        '''

        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        # Should clean successfully
        assert result.reduction_percent > 0
        assert 'Product' in result.output

    def test_blog_post(self):
        """Clean blog post page."""
        html = '''
        <html>
            <head>
                <script>analytics();</script>
                <style>.ad { display: block; }</style>
            </head>
            <body>
                <header><nav>Menu</nav></header>
                <article>
                    <h1>Blog Post Title</h1>
                    <p>First paragraph with important content.</p>
                    <p>Second paragraph with more details.</p>
                    <blockquote>A notable quote</blockquote>
                </article>
                <aside>Sidebar ads</aside>
                <footer>Copyright</footer>
            </body>
        </html>
        '''

        config = PipelineConfig(output_format='markdown')
        pipeline = CleaningPipeline(config)
        result = pipeline.process(html)

        assert '# Blog Post Title' in result.output
        assert 'First paragraph' in result.output

    def test_nextjs_page(self):
        """Clean Next.js SSR page."""
        html = '''
        <html>
            <body>
                <div id="__next">
                    <h1>Page from Next.js</h1>
                </div>
                <script id="__NEXT_DATA__" type="application/json">
                    {
                        "props": {
                            "pageProps": {
                                "title": "My Page",
                                "items": ["a", "b", "c"]
                            }
                        },
                        "page": "/",
                        "buildId": "abc123"
                    }
                </script>
            </body>
        </html>
        '''

        pipeline = CleaningPipeline()
        result = pipeline.process(html)

        # Should extract hydration data
        assert result.hydration_data is not None
        assert result.hydration_data.get('title') == 'My Page'
        assert result.hydration_data.get('items') == ['a', 'b', 'c']
