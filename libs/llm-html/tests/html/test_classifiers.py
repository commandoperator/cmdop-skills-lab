"""Tests for CSS class scoring and framework detection."""
import pytest

from llm_html.cleaner.classifiers.scorer import (
    ClassSemanticScorer,
    ClassCategory,
    ClassScore,
    score_class,
    filter_classes,
    clean_classes,
)
from llm_html.cleaner.classifiers.patterns import (
    FrameworkDetector,
    CSSFramework,
    detect_css_framework,
)


class TestClassSemanticScorer:
    """Tests for ClassSemanticScorer."""

    def test_semantic_classes_high_score(self):
        """Semantic business classes get high scores."""
        scorer = ClassSemanticScorer()

        # E-commerce
        assert scorer.score("product-card").score >= 0.8
        assert scorer.score("cart-item").score >= 0.8
        assert scorer.score("price").score >= 0.8
        assert scorer.score("checkout-form").score >= 0.8

        # Content
        assert scorer.score("title").score >= 0.7
        assert scorer.score("description").score >= 0.7
        assert scorer.score("author-name").score >= 0.7

    def test_structural_classes_medium_high_score(self):
        """Structural classes get medium-high scores."""
        scorer = ClassSemanticScorer()

        assert scorer.score("header").score >= 0.7
        assert scorer.score("navigation").score >= 0.7
        assert scorer.score("sidebar").score >= 0.7
        assert scorer.score("footer").score >= 0.7
        assert scorer.score("main-content").score >= 0.6

    def test_interactive_classes_medium_score(self):
        """Interactive/state classes get medium scores."""
        scorer = ClassSemanticScorer()

        assert scorer.score("active").score >= 0.5
        assert scorer.score("selected").score >= 0.5
        assert scorer.score("disabled").score >= 0.5
        assert scorer.score("is-open").score >= 0.4

    def test_utility_classes_scores(self):
        """Tailwind-style utility classes get appropriate scores."""
        scorer = ClassSemanticScorer()

        # Pure spacing classes (distinctly utility, no semantic overlap)
        assert scorer.score("p-4").score >= 0.3  # Gets utility score
        assert scorer.score("mt-2").score >= 0.3
        assert scorer.score("px-8").score >= 0.3

        # These should be kept (not hash classes)
        assert scorer.score("p-4").category != ClassCategory.HASH
        assert scorer.score("flex").category != ClassCategory.HASH
        assert scorer.score("rounded-lg").category != ClassCategory.HASH

        # Utility classes should be kept with default threshold
        kept = scorer.filter_classes(["p-4", "mt-2", "flex"])
        assert len(kept) == 3

    def test_hash_classes_low_score(self):
        """Generated/hash classes get very low scores."""
        scorer = ClassSemanticScorer()

        # styled-components
        assert scorer.score("css-abc123").score < 0.2
        assert scorer.score("sc-bdVaJa").score < 0.2

        # CSS Modules
        assert scorer.score("_a1b2c3d4").score < 0.2
        assert scorer.score("Component_abc123def").score < 0.3

        # Pure hashes
        assert scorer.score("abc123def").score < 0.1
        assert scorer.score("a1b2c3d4e5").score < 0.1

    def test_category_detection(self):
        """Categories are correctly detected."""
        scorer = ClassSemanticScorer()

        assert scorer.score("product-card").category == ClassCategory.SEMANTIC
        assert scorer.score("header").category == ClassCategory.STRUCTURAL
        assert scorer.score("active").category == ClassCategory.INTERACTIVE
        assert scorer.score("flex").category == ClassCategory.UTILITY
        assert scorer.score("css-abc123").category == ClassCategory.HASH

    def test_filter_classes(self):
        """Filter classes by threshold."""
        scorer = ClassSemanticScorer()

        classes = [
            "product-card",  # High score
            "css-abc123",    # Low score (hash)
            "flex",          # Medium score
            "p-4",           # Low-medium score
            "header",        # High score
            "_xyz789",       # Low score (CSS module)
        ]

        # Default threshold (0.3)
        kept = scorer.filter_classes(classes)
        assert "product-card" in kept
        assert "header" in kept
        assert "flex" in kept
        assert "css-abc123" not in kept
        assert "_xyz789" not in kept

        # Higher threshold
        kept_high = scorer.filter_classes(classes, threshold=0.6)
        assert "product-card" in kept_high
        assert "header" in kept_high
        assert "flex" not in kept_high

    def test_score_all(self):
        """Score multiple classes at once."""
        scorer = ClassSemanticScorer()

        classes = ["product-card", "flex", "css-abc123"]
        results = scorer.score_all(classes)

        assert len(results) == 3
        assert all(isinstance(r, ClassScore) for r in results)
        assert results[0].class_name == "product-card"
        assert results[0].score > results[2].score


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_score_class(self):
        """Test score_class function."""
        assert score_class("product-card") >= 0.8
        assert score_class("css-abc123") < 0.2
        assert score_class("flex") >= 0.3

    def test_filter_classes(self):
        """Test filter_classes function."""
        classes = ["product-card", "css-abc123", "header"]
        kept = filter_classes(classes)

        assert "product-card" in kept
        assert "header" in kept
        assert "css-abc123" not in kept

    def test_clean_classes(self):
        """Test clean_classes function."""
        class_string = "product-card css-abc123 flex p-4 _xyz789"
        cleaned = clean_classes(class_string)

        assert "product-card" in cleaned
        assert "flex" in cleaned
        assert "css-abc123" not in cleaned
        assert "_xyz789" not in cleaned


class TestFrameworkDetector:
    """Tests for CSS framework detection."""

    def test_detect_tailwind(self):
        """Detect Tailwind CSS."""
        detector = FrameworkDetector()

        classes = ["flex", "p-4", "bg-blue-500", "rounded-lg", "text-white"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.TAILWIND
        assert result.confidence > 0.5

    def test_detect_bootstrap(self):
        """Detect Bootstrap."""
        detector = FrameworkDetector()

        classes = ["container", "row", "col-md-6", "btn", "btn-primary"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.BOOTSTRAP
        assert result.confidence > 0.5

    def test_detect_material_ui(self):
        """Detect Material UI."""
        detector = FrameworkDetector()

        classes = ["MuiButton-root", "MuiButton-contained", "MuiTypography-h1"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.MATERIAL_UI
        assert result.confidence > 0.5

    def test_detect_chakra_ui(self):
        """Detect Chakra UI."""
        detector = FrameworkDetector()

        classes = ["chakra-button", "chakra-stack", "chakra-text"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.CHAKRA_UI

    def test_detect_ant_design(self):
        """Detect Ant Design."""
        detector = FrameworkDetector()

        classes = ["ant-btn", "ant-input", "ant-form-item"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.ANT_DESIGN

    def test_detect_styled_components(self):
        """Detect styled-components."""
        detector = FrameworkDetector()

        classes = ["sc-bdVaJa", "sc-htpNat", "css-1abc23"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.STYLED_COMPONENTS

    def test_detect_from_html(self):
        """Detect framework from HTML string."""
        detector = FrameworkDetector()

        html = '''
        <div class="flex p-4 bg-blue-500">
            <button class="rounded-lg text-white font-bold">
                Click me
            </button>
        </div>
        '''

        result = detector.detect_from_html(html)
        assert result.framework == CSSFramework.TAILWIND

    def test_detect_unknown(self):
        """Return unknown for unrecognized patterns."""
        detector = FrameworkDetector()

        classes = ["my-custom-class", "another-class"]
        result = detector.detect_from_classes(classes)

        assert result.framework == CSSFramework.UNKNOWN
        assert result.confidence == 0.0

    def test_secondary_frameworks(self):
        """Detect multiple frameworks."""
        detector = FrameworkDetector()

        # Mix of Tailwind and Bootstrap
        classes = ["flex", "p-4", "container", "row", "col-md-6"]
        result = detector.detect_from_classes(classes)

        # Should detect primary and have secondary
        assert result.framework in [CSSFramework.TAILWIND, CSSFramework.BOOTSTRAP]
        # May have secondary framework
        if len(result.secondary) > 0:
            assert result.secondary[0] in [CSSFramework.TAILWIND, CSSFramework.BOOTSTRAP]

    def test_removable_patterns(self):
        """Get patterns for removable classes."""
        detector = FrameworkDetector()

        # styled-components has removable hash classes
        patterns = detector.get_removable_patterns(CSSFramework.STYLED_COMPONENTS)
        assert len(patterns) > 0

        # Test patterns work
        import re
        test_class = "sc-bdVaJa"
        matches = [p for p in patterns if p.match(test_class)]
        assert len(matches) > 0


class TestDetectCSSFramework:
    """Tests for detect_css_framework convenience function."""

    def test_detect_from_list(self):
        """Detect from class list."""
        classes = ["MuiButton-root", "MuiButton-contained"]
        result = detect_css_framework(classes)
        assert result == CSSFramework.MATERIAL_UI

    def test_detect_from_html(self):
        """Detect from HTML string."""
        html = '<div class="ant-btn ant-btn-primary">Button</div>'
        result = detect_css_framework(html)
        assert result == CSSFramework.ANT_DESIGN


class TestRealWorldExamples:
    """Tests with real-world class combinations."""

    def test_ecommerce_product_card(self):
        """Test e-commerce product card classes."""
        scorer = ClassSemanticScorer()

        classes = [
            "product-card",
            "product-image",
            "product-title",
            "product-price",
            "add-to-cart-btn",
            "css-1abc23",  # styled-components hash
            "sc-bdVaJa",   # styled-components
            "flex",
            "p-4",
            "rounded-lg",
        ]

        kept = scorer.filter_classes(classes, threshold=0.3)

        # Semantic classes kept
        assert "product-card" in kept
        assert "product-title" in kept
        assert "product-price" in kept
        assert "add-to-cart-btn" in kept

        # Hash classes removed
        assert "css-1abc23" not in kept
        assert "sc-bdVaJa" not in kept

        # Utility classes may be kept or removed based on threshold
        # flex has score ~0.5, should be kept at 0.3 threshold
        assert "flex" in kept

    def test_navigation_classes(self):
        """Test navigation component classes."""
        scorer = ClassSemanticScorer()

        classes = [
            "main-nav",
            "nav-item",
            "nav-link",
            "active",
            "dropdown-menu",
            "_1a2b3c4d",  # CSS module hash
        ]

        kept = scorer.filter_classes(classes)

        assert "main-nav" in kept
        assert "nav-item" in kept
        assert "active" in kept
        assert "_1a2b3c4d" not in kept

    def test_form_classes(self):
        """Test form component classes."""
        scorer = ClassSemanticScorer()

        classes = [
            "form-group",
            "form-label",
            "form-input",
            "form-error",
            "submit-button",
            "disabled",
            "jss-123",  # MUI generated
        ]

        kept = scorer.filter_classes(classes)

        assert "form-group" in kept
        assert "form-label" in kept
        assert "submit-button" in kept
        assert "disabled" in kept
        assert "jss-123" not in kept
