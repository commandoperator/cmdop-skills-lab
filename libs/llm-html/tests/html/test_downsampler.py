"""Tests for D2Snap DOM downsampling."""
import pytest
from bs4 import BeautifulSoup

from llm_html.cleaner.transformers.downsampler import (
    D2SnapDownsampler,
    D2SnapConfig,
    DownsampleResult,
    DownsampleStats,
    downsample_html,
    estimate_tokens,
    calculate_ui_feature_score,
    is_essential_element,
    INTERACTIVE_ELEMENTS,
    SEMANTIC_ELEMENTS,
)


class TestUIFeatureScoring:
    """Tests for UI feature scoring."""

    def test_interactive_elements_high_score(self):
        """Interactive elements get high scores."""
        html = '<button>Click me</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        score = calculate_ui_feature_score(button)
        assert score >= 0.8

    def test_semantic_elements_medium_high_score(self):
        """Semantic elements get medium-high scores."""
        html = '<article><p>Content</p></article>'
        soup = BeautifulSoup(html, 'lxml')
        article = soup.find('article')

        score = calculate_ui_feature_score(article)
        assert score >= 0.5

    def test_element_with_id_high_score(self):
        """Elements with stable IDs get high scores."""
        html = '<div id="main-content">Content</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        score = calculate_ui_feature_score(div)
        assert score >= 0.6

    def test_element_with_testid_high_score(self):
        """Elements with test IDs get high scores."""
        html = '<div data-testid="product-card">Product</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        score = calculate_ui_feature_score(div)
        assert score >= 0.5

    def test_element_with_aria_medium_score(self):
        """Elements with ARIA attributes get medium scores."""
        html = '<div role="navigation" aria-label="Main menu">Nav</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        score = calculate_ui_feature_score(div)
        assert score >= 0.5

    def test_generic_container_low_score(self):
        """Generic containers without attributes get low scores."""
        html = '<div><span>text</span></div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        score = calculate_ui_feature_score(div)
        assert score < 0.3

    def test_heading_high_score(self):
        """Heading elements get high scores."""
        html = '<h1>Main Title</h1>'
        soup = BeautifulSoup(html, 'lxml')
        h1 = soup.find('h1')

        score = calculate_ui_feature_score(h1)
        assert score >= 0.7

    def test_link_with_href_medium_score(self):
        """Links with href get medium scores."""
        html = '<a href="/products">Products</a>'
        soup = BeautifulSoup(html, 'lxml')
        a = soup.find('a')

        score = calculate_ui_feature_score(a)
        assert score >= 0.8  # Interactive + href


class TestEssentialElements:
    """Tests for essential element detection."""

    def test_interactive_is_essential(self):
        """Interactive elements are essential."""
        html = '<button>Click</button>'
        soup = BeautifulSoup(html, 'lxml')
        button = soup.find('button')

        assert is_essential_element(button)

    def test_element_with_id_is_essential(self):
        """Elements with IDs are essential."""
        html = '<div id="important">Content</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        assert is_essential_element(div)

    def test_element_with_testid_is_essential(self):
        """Elements with test IDs are essential."""
        html = '<div data-testid="card">Content</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        assert is_essential_element(div)

    def test_generic_div_not_essential(self):
        """Generic divs are not essential."""
        html = '<div class="wrapper">Content</div>'
        soup = BeautifulSoup(html, 'lxml')
        div = soup.find('div')

        assert not is_essential_element(div)


class TestD2SnapDownsampler:
    """Tests for D2SnapDownsampler class."""

    def test_basic_downsampling(self):
        """Basic downsampling preserves structure."""
        html = '''
        <html>
            <body>
                <header id="header">Header</header>
                <main>
                    <article>
                        <h1>Title</h1>
                        <p>Content paragraph.</p>
                    </article>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        downsampler = D2SnapDownsampler()
        result = downsampler.downsample(soup)

        # Essential structure preserved
        assert result.soup.find('header')
        assert result.soup.find('h1')
        assert result.soup.find('article')

    def test_preserve_interactive_elements(self):
        """Interactive elements are preserved."""
        html = '''
        <div>
            <div class="wrapper">
                <div class="inner">
                    <button id="submit">Submit</button>
                    <a href="/link">Link</a>
                    <input type="text" name="field">
                </div>
            </div>
        </div>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(min_score_threshold=0.3)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        # All interactive elements preserved
        assert result.soup.find('button')
        assert result.soup.find('a')
        assert result.soup.find('input')

    def test_preserve_elements_with_ids(self):
        """Elements with IDs are preserved."""
        html = '''
        <div>
            <div id="important-section">
                <p>Important content</p>
            </div>
            <div class="generic">
                <p>Generic content</p>
            </div>
        </div>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(min_score_threshold=0.5)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        # Element with ID preserved
        assert result.soup.find('div', id='important-section')

    def test_consolidate_nested_containers(self):
        """Nested generic containers are consolidated."""
        html = '''
        <div class="level1">
            <div class="level2">
                <div class="level3">
                    <p>Deep content</p>
                </div>
            </div>
        </div>
        '''

        soup = BeautifulSoup(html, 'lxml')
        original_divs = len(soup.find_all('div'))

        config = D2SnapConfig(consolidation_depth=3)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        # Some nesting should be reduced
        final_divs = len(result.soup.find_all('div'))
        assert final_divs <= original_divs

        # Content preserved
        assert result.soup.find('p', string='Deep content')

    def test_truncate_repetitions(self):
        """Repeated elements are truncated."""
        html = '''
        <ul>
            <li class="item">Item 1</li>
            <li class="item">Item 2</li>
            <li class="item">Item 3</li>
            <li class="item">Item 4</li>
            <li class="item">Item 5</li>
            <li class="item">Item 6</li>
            <li class="item">Item 7</li>
            <li class="item">Item 8</li>
            <li class="item">Item 9</li>
            <li class="item">Item 10</li>
        </ul>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(max_repetitions=5)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        # Should have truncation marker
        marker = result.soup.find('span', attrs={'data-cmdop-truncated': True})
        if marker:
            assert 'more items' in marker.get_text()

    def test_stats_tracking(self):
        """Statistics are properly tracked."""
        html = '''
        <html>
            <body>
                <div><div><p>Content</p></div></div>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        downsampler = D2SnapDownsampler()
        result = downsampler.downsample(soup)

        assert result.stats.original_elements > 0
        assert result.stats.estimated_original_tokens > 0
        assert result.stats.estimated_final_tokens > 0


class TestAggressiveMode:
    """Tests for aggressive downsampling mode."""

    def test_aggressive_removes_styles(self):
        """Aggressive mode removes style tags."""
        html = '''
        <html>
            <head>
                <style>body { color: red; }</style>
            </head>
            <body>
                <p>Content</p>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(aggressive=True)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        assert result.soup.find('style') is None

    def test_aggressive_removes_extra_attributes(self):
        """Aggressive mode removes non-essential attributes."""
        html = '''
        <div id="main" data-analytics="track" onclick="handleClick()">
            Content
        </div>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(aggressive=True)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        div = result.soup.find('div')
        # Essential attributes preserved
        assert div.get('id') == 'main'
        # Non-essential removed
        assert div.get('data-analytics') is None
        assert div.get('onclick') is None


class TestD2SnapConfig:
    """Tests for D2SnapConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = D2SnapConfig()

        assert config.target_tokens == 10000
        assert config.min_score_threshold == 0.2
        assert config.consolidation_depth == 3
        assert config.max_repetitions == 5
        assert config.aggressive is False

    def test_custom_values(self):
        """Test custom configuration."""
        config = D2SnapConfig(
            target_tokens=5000,
            min_score_threshold=0.5,
            aggressive=True,
        )

        assert config.target_tokens == 5000
        assert config.min_score_threshold == 0.5
        assert config.aggressive is True


class TestDownsampleStats:
    """Tests for DownsampleStats."""

    def test_reduction_ratio(self):
        """Test reduction ratio calculation."""
        stats = DownsampleStats(
            estimated_original_tokens=10000,
            estimated_final_tokens=3000,
        )

        assert stats.reduction_ratio == 0.7

    def test_reduction_ratio_zero_original(self):
        """Handle zero original tokens."""
        stats = DownsampleStats(
            estimated_original_tokens=0,
            estimated_final_tokens=0,
        )

        assert stats.reduction_ratio == 0.0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_downsample_html_function(self):
        """Test downsample_html convenience function."""
        html = '''
        <html>
            <body>
                <div><div><div><p>Deep content</p></div></div></div>
            </body>
        </html>
        '''

        result = downsample_html(html, target_tokens=5000)

        assert 'Deep content' in result
        assert '<p>' in result

    def test_estimate_tokens(self):
        """Test token estimation."""
        html = 'a' * 400  # 400 characters

        tokens = estimate_tokens(html)
        assert tokens == 100  # 400 / 4


class TestRealWorldExamples:
    """Tests with real-world-like examples."""

    def test_product_listing_page(self):
        """Test with product listing structure."""
        # Generate many product cards
        cards = '\n'.join([
            f'''
            <div class="product-card">
                <img src="product{i}.jpg" alt="Product {i}">
                <h3>Product {i}</h3>
                <span class="price">${i * 10}.99</span>
                <button class="add-to-cart">Add to Cart</button>
            </div>
            '''
            for i in range(20)
        ])

        html = f'''
        <html>
            <body>
                <header id="header">
                    <nav>
                        <a href="/">Home</a>
                        <a href="/products">Products</a>
                    </nav>
                </header>
                <main>
                    <h1>Product Listing</h1>
                    <div class="products-grid">
                        {cards}
                    </div>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        config = D2SnapConfig(max_repetitions=5, target_tokens=5000)
        downsampler = D2SnapDownsampler(config)
        result = downsampler.downsample(soup)

        # Header and footer preserved
        assert result.soup.find('header')
        assert result.soup.find('footer')

        # Navigation links preserved
        assert len(result.soup.find_all('a')) >= 2

        # Some products preserved, but not all
        remaining_cards = result.soup.find_all('div', class_='product-card')
        assert len(remaining_cards) <= 10

        # Buttons preserved
        assert result.soup.find('button')

    def test_form_page(self):
        """Test with form structure."""
        html = '''
        <html>
            <body>
                <main>
                    <h1>Contact Us</h1>
                    <form id="contact-form">
                        <div class="form-group">
                            <label for="name">Name</label>
                            <input type="text" id="name" name="name">
                        </div>
                        <div class="form-group">
                            <label for="email">Email</label>
                            <input type="email" id="email" name="email">
                        </div>
                        <div class="form-group">
                            <label for="message">Message</label>
                            <textarea id="message" name="message"></textarea>
                        </div>
                        <button type="submit">Send</button>
                    </form>
                </main>
            </body>
        </html>
        '''

        soup = BeautifulSoup(html, 'lxml')
        downsampler = D2SnapDownsampler()
        result = downsampler.downsample(soup)

        # Form preserved
        assert result.soup.find('form')

        # All inputs preserved
        assert len(result.soup.find_all('input')) == 2
        assert result.soup.find('textarea')

        # Submit button preserved
        assert result.soup.find('button')

        # Labels preserved (important for accessibility)
        assert len(result.soup.find_all('label')) == 3
