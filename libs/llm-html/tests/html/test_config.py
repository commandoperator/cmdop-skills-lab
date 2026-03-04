"""Tests for HTML Cleaner configuration."""
import pytest

from llm_html.cleaner.config import (
    CleaningConfig,
    FocusedCleaningConfig,
    SELECTION_MARKER_ATTR,
    AGGRESSIVE_NOISE_TAGS,
    FOCUSED_NOISE_TAGS,
    KEEP_ATTRIBUTES,
    REMOVE_ATTRIBUTES,
    HASH_CLASS_PATTERNS,
    SEMANTIC_CLASS_PATTERNS,
    MAX_HTML_SIZE,
    MAX_TEXT_LENGTH_STAGE1,
    MAX_TEXT_LENGTH_STAGE2,
)


class TestSelectionMarker:
    """Tests for selection marker configuration."""

    def test_marker_attr_is_cmdop(self):
        """Selection marker should use cmdop prefix."""
        assert SELECTION_MARKER_ATTR == "data-cmdop-id"

    def test_marker_in_keep_attributes(self):
        """Selection marker should be in keep attributes."""
        assert SELECTION_MARKER_ATTR in KEEP_ATTRIBUTES


class TestNoiseTags:
    """Tests for noise tag configuration."""

    def test_aggressive_includes_forms(self):
        """Aggressive mode should remove form elements."""
        assert "form" in AGGRESSIVE_NOISE_TAGS
        assert "input" not in AGGRESSIVE_NOISE_TAGS  # Too aggressive

    def test_focused_excludes_forms(self):
        """Focused mode should keep form elements."""
        assert "form" not in FOCUSED_NOISE_TAGS

    def test_both_remove_scripts(self):
        """Both modes should remove scripts."""
        assert "script" in AGGRESSIVE_NOISE_TAGS
        assert "script" in FOCUSED_NOISE_TAGS

    def test_both_remove_styles(self):
        """Both modes should remove styles."""
        assert "style" in AGGRESSIVE_NOISE_TAGS
        assert "style" in FOCUSED_NOISE_TAGS

    def test_aggressive_removes_layout(self):
        """Aggressive mode removes layout elements."""
        assert "header" in AGGRESSIVE_NOISE_TAGS
        assert "footer" in AGGRESSIVE_NOISE_TAGS
        assert "nav" in AGGRESSIVE_NOISE_TAGS
        assert "aside" in AGGRESSIVE_NOISE_TAGS


class TestAttributes:
    """Tests for attribute configuration."""

    def test_keep_essential_attributes(self):
        """Essential attributes should be kept."""
        essential = ["id", "class", "href", "src", "alt", "title"]
        for attr in essential:
            assert attr in KEEP_ATTRIBUTES

    def test_remove_event_handlers(self):
        """Event handler attributes should be removed."""
        events = ["onclick", "onload", "onerror", "onchange"]
        for attr in events:
            assert attr in REMOVE_ATTRIBUTES

    def test_remove_tracking(self):
        """Tracking attributes should be removed."""
        tracking = ["data-gtm", "data-analytics", "data-tracking", "data-ga"]
        for attr in tracking:
            assert attr in REMOVE_ATTRIBUTES

    def test_remove_style(self):
        """Style attribute should be removed."""
        assert "style" in REMOVE_ATTRIBUTES


class TestCSSPatterns:
    """Tests for CSS class pattern configuration."""

    def test_hash_patterns_detect_generated(self):
        """Hash patterns should detect auto-generated classes."""
        generated_classes = [
            "x16tdsg8",      # Facebook
            "_1a2b3c4d",     # CSS modules
            "css-abc123",   # styled-components
            "sc-bdVaJa",    # styled-components v2
            "jsx-123456",   # JSX
            "emotion-xyz",  # Emotion
        ]
        for cls in generated_classes:
            matched = any(p.match(cls) for p in HASH_CLASS_PATTERNS)
            assert matched, f"Should detect {cls} as generated"

    def test_hash_patterns_skip_semantic(self):
        """Hash patterns should not match semantic classes."""
        semantic_classes = ["header", "content", "button", "card"]
        for cls in semantic_classes:
            matched = any(p.match(cls) for p in HASH_CLASS_PATTERNS)
            assert not matched, f"Should not match semantic class {cls}"

    def test_semantic_patterns_detect_meaningful(self):
        """Semantic patterns should detect meaningful classes."""
        semantic_classes = ["header", "footer", "title", "content", "product", "price"]
        for cls in semantic_classes:
            matched = any(p.match(cls) for p in SEMANTIC_CLASS_PATTERNS)
            assert matched, f"Should detect {cls} as semantic"


class TestSizeLimits:
    """Tests for size limit configuration."""

    def test_max_html_size(self):
        """Max HTML size should be 2MB."""
        assert MAX_HTML_SIZE == 2_000_000

    def test_text_length_stage1_smaller(self):
        """Stage 1 text length should be smaller than Stage 2."""
        assert MAX_TEXT_LENGTH_STAGE1 < MAX_TEXT_LENGTH_STAGE2

    def test_text_length_stage1(self):
        """Stage 1 text length should be 500."""
        assert MAX_TEXT_LENGTH_STAGE1 == 500

    def test_text_length_stage2(self):
        """Stage 2 text length should be 1000."""
        assert MAX_TEXT_LENGTH_STAGE2 == 1000


class TestCleaningConfig:
    """Tests for CleaningConfig dataclass."""

    def test_default_config(self):
        """Default config should have expected values."""
        config = CleaningConfig()
        assert config.max_html_size == MAX_HTML_SIZE
        assert config.remove_scripts is True
        assert config.remove_styles is True
        assert config.clean_attributes is True

    def test_custom_config(self):
        """Custom config values should override defaults."""
        config = CleaningConfig(
            max_html_size=100_000,
            remove_scripts=False,
            max_text_length=200,
        )
        assert config.max_html_size == 100_000
        assert config.remove_scripts is False
        assert config.max_text_length == 200


class TestFocusedCleaningConfig:
    """Tests for FocusedCleaningConfig dataclass."""

    def test_focused_has_larger_text_limit(self):
        """Focused config should have larger text limit."""
        config = FocusedCleaningConfig()
        assert config.max_text_length == MAX_TEXT_LENGTH_STAGE2

    def test_focused_uses_focused_tags(self):
        """Focused config should use focused noise tags."""
        config = FocusedCleaningConfig()
        assert config.noise_tags == FOCUSED_NOISE_TAGS
