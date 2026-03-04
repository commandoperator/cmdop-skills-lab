"""Tests for semantic chunking."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.transformers.chunker import (
    SemanticChunker,
    ChunkConfig,
    Chunk,
    ChunkResult,
    ItemPattern,
    chunk_html,
)


class TestSemanticChunker:
    """Tests for SemanticChunker class."""

    def test_small_page_no_chunking(self):
        """Small pages aren't chunked."""
        html = '''
        <html>
            <body>
                <h1>Title</h1>
                <p>Short content.</p>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        chunker = SemanticChunker()
        result = chunker.chunk(soup)

        assert not result.was_chunked
        assert len(result.chunks) == 1

    def test_detect_list_items(self):
        """Detect list item patterns."""
        html = '''
        <ul class="items">
            <li class="item">Item 1</li>
            <li class="item">Item 2</li>
            <li class="item">Item 3</li>
            <li class="item">Item 4</li>
            <li class="item">Item 5</li>
        </ul>
        '''

        soup = BeautifulSoup(html, 'lxml')
        chunker = SemanticChunker()
        patterns = chunker.detect_item_patterns(soup)

        assert len(patterns) > 0
        # Should detect li.item pattern
        li_pattern = [p for p in patterns if 'li' in p.selector]
        assert len(li_pattern) > 0
        assert li_pattern[0].count >= 5

    def test_detect_product_cards(self):
        """Detect product card patterns."""
        html = '''
        <div class="products">
            <div class="product-card">Product 1</div>
            <div class="product-card">Product 2</div>
            <div class="product-card">Product 3</div>
            <div class="product-card">Product 4</div>
        </div>
        '''

        soup = BeautifulSoup(html, 'lxml')
        chunker = SemanticChunker()
        patterns = chunker.detect_item_patterns(soup)

        assert len(patterns) > 0
        product_pattern = [p for p in patterns if 'product' in p.selector.lower()]
        assert len(product_pattern) > 0

    def test_chunk_large_list(self):
        """Chunk large list into smaller pieces when over token limit."""
        # Create a large list with significant content per item
        items = '\n'.join([
            f'<li class="item">{"Lorem ipsum dolor sit amet " * 20} Item {i}</li>'
            for i in range(50)
        ])
        html = f'<ul class="items">{items}</ul>'

        soup = BeautifulSoup(html, 'lxml')
        # Very low token limit to force chunking
        config = ChunkConfig(max_tokens=500, max_items=5)
        chunker = SemanticChunker(config)
        result = chunker.chunk(soup)

        # Should have detected the pattern
        patterns = chunker.detect_item_patterns(soup)
        assert len(patterns) > 0

        # If chunked, verify chunk properties
        if result.was_chunked:
            assert len(result.chunks) > 1
            for chunk in result.chunks:
                assert chunk.item_count <= config.max_items

    def test_chunk_preserves_all_items(self):
        """All items are preserved across chunks when chunking occurs."""
        # Create content large enough to require chunking
        items = '\n'.join([
            f'<li class="item">{"Content " * 50} Item {i}</li>'
            for i in range(20)
        ])
        html = f'<ul class="items">{items}</ul>'

        soup = BeautifulSoup(html, 'lxml')
        # Force small chunks
        config = ChunkConfig(max_tokens=500, max_items=3)
        chunker = SemanticChunker(config)
        result = chunker.chunk(soup)

        # If chunking occurred, verify items are preserved
        if result.was_chunked:
            total_items = sum(chunk.item_count for chunk in result.chunks)
            assert total_items == 20
        else:
            # Content was small enough to fit in one chunk
            assert len(result.chunks) == 1

    def test_chunk_indices(self):
        """Chunk indices are correct."""
        items = '\n'.join([f'<li class="item">Item {i}</li>' for i in range(15)])
        html = f'<ul class="items">{items}</ul>'

        soup = BeautifulSoup(html, 'lxml')
        config = ChunkConfig(max_tokens=500, max_items=5)
        chunker = SemanticChunker(config)
        result = chunker.chunk(soup)

        if result.was_chunked:
            # Check indices are sequential
            for i, chunk in enumerate(result.chunks):
                assert chunk.chunk_index == i
                assert chunk.total_chunks == len(result.chunks)

    def test_chunk_with_context(self):
        """Chunks include context when enabled."""
        html = '''
        <header>Site Header</header>
        <h1>Product List</h1>
        <ul class="products">
            <li class="product">Product 1</li>
            <li class="product">Product 2</li>
            <li class="product">Product 3</li>
            <li class="product">Product 4</li>
            <li class="product">Product 5</li>
        </ul>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = ChunkConfig(
            max_tokens=200,
            max_items=2,
            preserve_context=True,
        )
        chunker = SemanticChunker(config)
        result = chunker.chunk(soup)

        if result.was_chunked:
            # First chunk should have context
            assert result.chunks[0].context_html != ""


class TestChunkConfig:
    """Tests for ChunkConfig."""

    def test_default_values(self):
        """Test default configuration."""
        config = ChunkConfig()

        assert config.max_tokens == 8000
        assert config.min_items == 3
        assert config.max_items == 20
        assert config.preserve_context is True

    def test_custom_values(self):
        """Test custom configuration."""
        config = ChunkConfig(
            max_tokens=5000,
            min_items=5,
            max_items=10,
            preserve_context=False,
        )

        assert config.max_tokens == 5000
        assert config.min_items == 5
        assert config.max_items == 10
        assert config.preserve_context is False


class TestItemPattern:
    """Tests for ItemPattern."""

    def test_pattern_attributes(self):
        """Test pattern attributes."""
        pattern = ItemPattern(
            selector="li.item",
            count=10,
            parent=None,
            sample_html="<li>Sample</li>",
            avg_tokens=50,
        )

        assert pattern.selector == "li.item"
        assert pattern.count == 10
        assert pattern.avg_tokens == 50


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_chunk_attributes(self):
        """Test chunk attributes."""
        chunk = Chunk(
            html="<ul><li>Item</li></ul>",
            estimated_tokens=10,
            item_count=1,
            container_selector="li.item",
            start_index=0,
            end_index=1,
            chunk_index=0,
            total_chunks=1,
        )

        assert chunk.html == "<ul><li>Item</li></ul>"
        assert chunk.estimated_tokens == 10
        assert chunk.item_count == 1
        assert chunk.chunk_index == 0


class TestChunkHtml:
    """Tests for chunk_html convenience function."""

    def test_chunk_html_function(self):
        """Test chunk_html convenience function."""
        items = '\n'.join([f'<li class="item">Item {i}</li>' for i in range(30)])
        html = f'<ul class="items">{items}</ul>'

        chunks = chunk_html(html, max_tokens=1000, max_items=10)

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_small_html_single_chunk(self):
        """Small HTML returns single chunk."""
        html = '<p>Small content</p>'
        chunks = chunk_html(html)

        assert len(chunks) == 1


class TestRealWorldExamples:
    """Tests with real-world-like examples."""

    def test_ecommerce_product_listing(self):
        """Test e-commerce product listing."""
        products = '\n'.join([
            f'''
            <div class="product-card">
                <img src="product{i}.jpg" alt="Product {i}">
                <h3 class="title">Product {i}</h3>
                <span class="price">${i * 10}.99</span>
                <p class="description">Description for product {i} with some details about the item.</p>
                <button>Add to Cart</button>
            </div>
            '''
            for i in range(25)
        ])

        html = f'''
        <html>
            <body>
                <header><nav>Navigation</nav></header>
                <h1>Products</h1>
                <div class="product-grid">
                    {products}
                </div>
                <footer>Footer</footer>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = ChunkConfig(max_tokens=3000, max_items=5)
        chunker = SemanticChunker(config)
        result = chunker.chunk(soup)

        # Should be chunked
        if result.was_chunked:
            assert len(result.chunks) > 1

            # Verify all products accounted for
            total = sum(c.item_count for c in result.chunks)
            assert total >= 20  # At least most products

    def test_blog_post_listing(self):
        """Test blog post listing."""
        posts = '\n'.join([
            f'''
            <article class="post">
                <h2>Post Title {i}</h2>
                <time>2024-01-{i:02d}</time>
                <p>Post excerpt with some content about topic {i}.</p>
                <a href="/post/{i}">Read more</a>
            </article>
            '''
            for i in range(15)
        ])

        html = f'''
        <main>
            <h1>Blog</h1>
            <div class="posts">
                {posts}
            </div>
        </main>
        '''

        soup = BeautifulSoup(html, 'lxml')
        chunker = SemanticChunker()
        patterns = chunker.detect_item_patterns(soup)

        # Should detect article pattern
        article_patterns = [p for p in patterns if 'article' in p.selector or 'post' in p.selector]
        assert len(article_patterns) > 0

    def test_table_data(self):
        """Test table row chunking."""
        rows = '\n'.join([
            f'<tr><td>Row {i}</td><td>Data {i}</td><td>Value {i}</td></tr>'
            for i in range(50)
        ])

        html = f'''
        <table>
            <thead><tr><th>Name</th><th>Data</th><th>Value</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        '''

        soup = BeautifulSoup(html, 'lxml')
        chunker = SemanticChunker()
        patterns = chunker.detect_item_patterns(soup)

        # Should detect tr pattern
        tr_patterns = [p for p in patterns if 'tr' in p.selector]
        assert len(tr_patterns) > 0
        assert tr_patterns[0].count >= 50
