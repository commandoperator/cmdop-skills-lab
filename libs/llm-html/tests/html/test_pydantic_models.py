"""Tests for Pydantic 2 models and HTMLCleaner.

Tests the new Pydantic-based API introduced in Phase 9.
"""
import pytest
from pydantic import ValidationError

from llm_html import (
    # Models
    OutputFormat,
    CleanerConfig,
    CleanerStats,
    ChunkInfo,
    CleanerResult,
    # Cleaner
    HTMLCleaner,
    clean,
    clean_to_json,
)


# =============================================================================
# OutputFormat Tests
# =============================================================================

class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_default_values(self):
        """Test all format values exist."""
        assert OutputFormat.HTML.value == "html"
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.AOM.value == "aom"
        assert OutputFormat.XTREE.value == "xtree"

    def test_string_enum(self):
        """Test that OutputFormat is a string enum."""
        assert isinstance(OutputFormat.HTML, str)
        assert OutputFormat.HTML == "html"


# =============================================================================
# CleanerConfig Tests
# =============================================================================

class TestCleanerConfig:
    """Tests for CleanerConfig model."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CleanerConfig()

        assert config.max_tokens == 10000
        assert config.output_format == OutputFormat.HTML
        assert config.remove_scripts is True
        assert config.remove_styles is True
        assert config.remove_comments is True
        assert config.remove_hidden is True
        assert config.remove_empty is True
        assert config.filter_classes is True
        assert config.class_threshold == 0.3
        assert config.enable_chunking is True
        assert config.chunk_max_items == 20
        assert config.try_hydration is True
        assert config.preserve_selectors == []

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CleanerConfig(
            max_tokens=5000,
            output_format=OutputFormat.MARKDOWN,
            filter_classes=False,
            class_threshold=0.5,
        )

        assert config.max_tokens == 5000
        assert config.output_format == OutputFormat.MARKDOWN
        assert config.filter_classes is False
        assert config.class_threshold == 0.5

    def test_validation_max_tokens_min(self):
        """Test max_tokens minimum validation."""
        with pytest.raises(ValidationError):
            CleanerConfig(max_tokens=50)  # Below minimum 100

    def test_validation_max_tokens_max(self):
        """Test max_tokens maximum validation."""
        with pytest.raises(ValidationError):
            CleanerConfig(max_tokens=200000)  # Above maximum 100000

    def test_validation_class_threshold_range(self):
        """Test class_threshold range validation."""
        # Valid values
        CleanerConfig(class_threshold=0.0)
        CleanerConfig(class_threshold=1.0)
        CleanerConfig(class_threshold=0.5)

        # Invalid values
        with pytest.raises(ValidationError):
            CleanerConfig(class_threshold=-0.1)

        with pytest.raises(ValidationError):
            CleanerConfig(class_threshold=1.1)

    def test_json_serialization(self):
        """Test JSON serialization."""
        config = CleanerConfig(max_tokens=5000)
        json_str = config.model_dump_json()

        assert "5000" in json_str
        assert "max_tokens" in json_str


# =============================================================================
# CleanerStats Tests
# =============================================================================

class TestCleanerStats:
    """Tests for CleanerStats model."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = CleanerStats()

        assert stats.original_size == 0
        assert stats.cleaned_size == 0
        assert stats.original_tokens == 0
        assert stats.cleaned_tokens == 0
        assert stats.scripts_removed == 0
        assert stats.styles_removed == 0
        assert stats.comments_removed == 0
        assert stats.hidden_removed == 0
        assert stats.empty_removed == 0
        assert stats.elements_removed == 0
        assert stats.classes_total == 0
        assert stats.classes_removed == 0
        assert stats.classes_kept == 0
        assert stats.processing_time_ms == 0.0

    def test_computed_reduction_percent(self):
        """Test reduction_percent computed field."""
        stats = CleanerStats(original_size=1000, cleaned_size=300)
        assert stats.reduction_percent == 70.0

        stats = CleanerStats(original_size=1000, cleaned_size=500)
        assert stats.reduction_percent == 50.0

    def test_computed_reduction_percent_zero_original(self):
        """Test reduction_percent with zero original size."""
        stats = CleanerStats(original_size=0, cleaned_size=0)
        assert stats.reduction_percent == 0.0

    def test_computed_token_reduction_percent(self):
        """Test token_reduction_percent computed field."""
        stats = CleanerStats(original_tokens=1000, cleaned_tokens=250)
        assert stats.token_reduction_percent == 75.0

    def test_computed_compression_ratio(self):
        """Test compression_ratio computed field."""
        stats = CleanerStats(original_size=1000, cleaned_size=250)
        assert stats.compression_ratio == 4.0

        stats = CleanerStats(original_size=1000, cleaned_size=500)
        assert stats.compression_ratio == 2.0

    def test_computed_compression_ratio_zero_cleaned(self):
        """Test compression_ratio with zero cleaned size."""
        stats = CleanerStats(original_size=1000, cleaned_size=0)
        assert stats.compression_ratio == 0.0


# =============================================================================
# ChunkInfo Tests
# =============================================================================

class TestChunkInfo:
    """Tests for ChunkInfo model."""

    def test_creation(self):
        """Test chunk info creation."""
        chunk = ChunkInfo(index=0, html="<div>Test</div>", tokens=10, items=1)

        assert chunk.index == 0
        assert chunk.html == "<div>Test</div>"
        assert chunk.tokens == 10
        assert chunk.items == 1

    def test_default_values(self):
        """Test default values for optional fields."""
        chunk = ChunkInfo(index=0, html="<p>Test</p>")

        assert chunk.tokens == 0
        assert chunk.items == 0


# =============================================================================
# CleanerResult Tests
# =============================================================================

class TestCleanerResult:
    """Tests for CleanerResult model."""

    def test_default_values(self):
        """Test default result values."""
        result = CleanerResult()

        assert result.html == ""
        assert result.output == ""
        assert result.hydration_data is None
        assert result.structured_data is None
        assert result.was_chunked is False
        assert result.chunks == []
        assert result.total_chunks == 0
        assert result.extraction_method is None
        assert result.framework_detected is None
        assert result.output_format == OutputFormat.HTML

    def test_computed_success(self):
        """Test success computed field."""
        # Success with HTML
        result = CleanerResult(html="<div>Test</div>")
        assert result.success is True

        # Success with hydration data
        result = CleanerResult(hydration_data={"key": "value"})
        assert result.success is True

        # Failure (empty)
        result = CleanerResult()
        assert result.success is False

    def test_computed_has_hydration(self):
        """Test has_hydration computed field."""
        result = CleanerResult(hydration_data={"key": "value"})
        assert result.has_hydration is True

        result = CleanerResult()
        assert result.has_hydration is False


# =============================================================================
# HTMLCleaner Tests
# =============================================================================

class TestHTMLCleaner:
    """Tests for HTMLCleaner class."""

    @pytest.fixture
    def sample_html(self):
        """Sample HTML for testing."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <script>console.log('test');</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <div class="container mx-auto px-4">
                <h1>Hello World</h1>
                <p style="color: blue;">Test paragraph</p>
                <!-- This is a comment -->
                <div hidden>Hidden content</div>
            </div>
        </body>
        </html>
        """

    def test_default_config(self):
        """Test cleaner with default configuration."""
        cleaner = HTMLCleaner()
        assert cleaner.config.max_tokens == 10000
        assert cleaner.config.output_format == OutputFormat.HTML

    def test_custom_config(self):
        """Test cleaner with custom configuration."""
        config = CleanerConfig(max_tokens=5000)
        cleaner = HTMLCleaner(config)
        assert cleaner.config.max_tokens == 5000

    def test_clean_returns_result(self, sample_html):
        """Test that clean returns CleanerResult."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert isinstance(result, CleanerResult)
        assert result.success is True
        assert result.extraction_method == "dom"

    def test_clean_removes_scripts(self, sample_html):
        """Test script removal."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.scripts_removed >= 1
        assert "<script>" not in result.html

    def test_clean_removes_styles(self, sample_html):
        """Test style removal."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.styles_removed >= 1
        assert "<style>" not in result.html

    def test_clean_removes_comments(self, sample_html):
        """Test comment removal."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.comments_removed >= 1
        assert "This is a comment" not in result.html

    def test_clean_removes_hidden(self, sample_html):
        """Test hidden element removal."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.hidden_removed >= 1
        assert "Hidden content" not in result.html

    def test_clean_stats_sizes(self, sample_html):
        """Test that stats track sizes correctly."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.original_size > 0
        assert result.stats.cleaned_size > 0
        assert result.stats.cleaned_size < result.stats.original_size

    def test_clean_stats_reduction(self, sample_html):
        """Test reduction statistics."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.reduction_percent > 0
        assert result.stats.compression_ratio > 1.0

    def test_clean_processing_time(self, sample_html):
        """Test processing time tracking."""
        cleaner = HTMLCleaner()
        result = cleaner.clean(sample_html)

        assert result.stats.processing_time_ms > 0

    def test_clean_with_config_override(self, sample_html):
        """Test config override on clean call."""
        cleaner = HTMLCleaner()  # Default config
        custom_config = CleanerConfig(remove_scripts=False)
        result = cleaner.clean(sample_html, config=custom_config)

        # Scripts should still be in the output
        assert "<script>" in result.html or result.stats.scripts_removed == 0

    def test_clean_markdown_output(self, sample_html):
        """Test Markdown output format."""
        config = CleanerConfig(output_format=OutputFormat.MARKDOWN)
        cleaner = HTMLCleaner(config)
        result = cleaner.clean(sample_html)

        assert result.output_format == OutputFormat.MARKDOWN
        # Markdown typically contains # for headers
        assert "Hello World" in result.output


# =============================================================================
# Convenience Functions Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def sample_html(self):
        """Sample HTML for testing."""
        return """
        <html>
        <head><script>test</script></head>
        <body><h1>Hello</h1><p>World</p></body>
        </html>
        """

    def test_clean(self, sample_html):
        """Test clean function."""
        result = clean(sample_html)

        assert isinstance(result, CleanerResult)
        assert result.success is True
        assert "Hello" in result.html
        assert "<script>" not in result.html

    def test_clean_with_options(self, sample_html):
        """Test clean with options."""
        result = clean(
            sample_html,
            max_tokens=5000,
            output_format="markdown",
        )

        assert isinstance(result, CleanerResult)
        assert result.output_format == OutputFormat.MARKDOWN

    def test_clean_to_json_no_hydration(self, sample_html):
        """Test clean_to_json returns HTML when no hydration data."""
        result = clean_to_json(sample_html)

        # No hydration data, should return cleaned HTML
        assert isinstance(result, str)
        assert "Hello" in result


# =============================================================================
# Hydration Extraction Tests
# =============================================================================

class TestHydrationExtraction:
    """Tests for hydration-first strategy."""

    def test_nextjs_hydration(self):
        """Test Next.js hydration extraction."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script id="__NEXT_DATA__" type="application/json">
                {"props": {"pageProps": {"products": [{"name": "Test"}]}}}
            </script>
        </head>
        <body>
            <div id="__next">Content</div>
        </body>
        </html>
        """

        cleaner = HTMLCleaner()
        result = cleaner.clean(html)

        # Should extract hydration data
        assert result.has_hydration is True
        assert result.hydration_data is not None
        assert result.extraction_method == "hydration"

    def test_clean_to_json_with_hydration(self):
        """Test clean_to_json returns dict when hydration data found."""
        html = """
        <html>
        <head>
            <script id="__NEXT_DATA__" type="application/json">
                {"props": {"pageProps": {"products": [{"name": "Widget"}]}}}
            </script>
        </head>
        <body></body>
        </html>
        """

        result = clean_to_json(html)

        assert isinstance(result, dict)
        assert "products" in result


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_html(self):
        """Test with empty HTML."""
        cleaner = HTMLCleaner()
        result = cleaner.clean("")

        assert result.stats.original_size == 0
        assert result.success is False

    def test_minimal_html(self):
        """Test with minimal HTML."""
        cleaner = HTMLCleaner()
        result = cleaner.clean("<p>Test</p>")

        assert result.success is True
        assert "Test" in result.html

    def test_very_large_html(self):
        """Test with large HTML content."""
        large_html = "<html><body>" + "<p>Test</p>" * 1000 + "</body></html>"

        cleaner = HTMLCleaner()
        result = cleaner.clean(large_html)

        assert result.success is True
        assert result.stats.original_size > 10000

    def test_nested_elements(self):
        """Test with deeply nested elements."""
        nested = "<div>" * 50 + "Content" + "</div>" * 50

        cleaner = HTMLCleaner()
        result = cleaner.clean(nested)

        assert result.success is True
        assert "Content" in result.html

    def test_special_characters(self):
        """Test with special characters."""
        html = "<p>Test &amp; Test &lt;special&gt; Test</p>"

        cleaner = HTMLCleaner()
        result = cleaner.clean(html)

        assert result.success is True
