"""CSS class semantic scoring for LLM-optimized HTML.

Scores CSS classes by their semantic relevance for understanding UI structure.
High-scoring classes (like 'product-card', 'btn-primary') are kept,
while low-scoring classes (like 'css-abc123', '_a1b2c3') are removed.

Categories:
- Semantic: Business domain classes (product, cart, user, etc.)
- Structural: Layout/structure classes (header, nav, main, etc.)
- Interactive: State/action classes (active, selected, disabled, etc.)
- Utility: Tailwind-style utility classes (flex, p-4, text-lg, etc.)
- Framework: Component library classes (MuiButton, chakra-*, ant-*, etc.)
- Hash: Generated/obfuscated classes (css-*, sc-*, _abc123, etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class ClassCategory(Enum):
    """Category of CSS class."""

    SEMANTIC = "semantic"
    """Business domain classes: product, cart, user, price, etc."""

    STRUCTURAL = "structural"
    """Layout/structure: header, nav, main, sidebar, footer, etc."""

    INTERACTIVE = "interactive"
    """State/action: active, selected, disabled, loading, etc."""

    UTILITY = "utility"
    """Tailwind-style utilities: flex, p-4, text-lg, etc."""

    FRAMEWORK = "framework"
    """Component libraries: Mui*, chakra-*, ant-*, etc."""

    HASH = "hash"
    """Generated/obfuscated: css-*, sc-*, _abc123, etc."""

    UNKNOWN = "unknown"
    """Unclassified classes."""


@dataclass
class ClassScore:
    """Score result for a CSS class."""

    class_name: str
    """The CSS class name."""

    score: float
    """Semantic score from 0.0 to 1.0."""

    category: ClassCategory
    """Detected category."""

    keep: bool
    """Whether to keep this class based on threshold."""


# =============================================================================
# Pattern Definitions
# =============================================================================

# Semantic patterns - Business domain (HIGH value)
SEMANTIC_PATTERNS: List[Tuple[re.Pattern, float]] = [
    # E-commerce
    (re.compile(r'^(product|item|cart|checkout|price|buy|shop)', re.I), 0.95),
    (re.compile(r'(product|item|card|listing|catalog)[-_]', re.I), 0.9),
    (re.compile(r'[-_](product|item|price|cart|buy)$', re.I), 0.9),

    # Content
    (re.compile(r'^(title|name|desc|description|content|text|body)', re.I), 0.85),
    (re.compile(r'^(image|img|photo|picture|thumbnail|avatar)', re.I), 0.8),
    (re.compile(r'^(author|date|time|meta|tag|category)', re.I), 0.75),

    # User/Auth
    (re.compile(r'^(user|profile|account|auth|login|signup)', re.I), 0.85),
    (re.compile(r'^(avatar|username|email|password)', re.I), 0.8),

    # Actions
    (re.compile(r'^(btn|button|link|action|submit|cancel)', re.I), 0.8),
    (re.compile(r'^(add|remove|edit|delete|save|update)', re.I), 0.75),

    # Lists/Tables
    (re.compile(r'^(list|table|row|cell|column|grid)', re.I), 0.75),
    (re.compile(r'^(item|entry|record|result)', re.I), 0.7),
]

# Structural patterns - Layout (MEDIUM-HIGH value)
STRUCTURAL_PATTERNS: List[Tuple[re.Pattern, float]] = [
    (re.compile(r'^(header|footer|nav|navigation|sidebar|aside)', re.I), 0.85),
    (re.compile(r'^(main|content|body|wrapper|container)', re.I), 0.8),
    (re.compile(r'^(section|article|page|view|panel)', re.I), 0.75),
    (re.compile(r'^(modal|dialog|popup|overlay|drawer)', re.I), 0.75),
    (re.compile(r'^(menu|dropdown|tabs?|accordion)', re.I), 0.7),
    (re.compile(r'^(form|input|field|label|control)', re.I), 0.7),
    (re.compile(r'^(card|box|block|widget|component)', re.I), 0.65),
]

# Interactive/State patterns (MEDIUM value)
INTERACTIVE_PATTERNS: List[Tuple[re.Pattern, float]] = [
    (re.compile(r'^(active|selected|current|focused|hover)', re.I), 0.7),
    (re.compile(r'^(disabled|readonly|hidden|visible)', re.I), 0.65),
    (re.compile(r'^(loading|pending|processing|busy)', re.I), 0.6),
    (re.compile(r'^(error|warning|success|info|alert)', re.I), 0.65),
    (re.compile(r'^(open|closed|expanded|collapsed)', re.I), 0.6),
    (re.compile(r'^(is[-_]|has[-_])', re.I), 0.55),
]

# Utility patterns - Tailwind/Bootstrap style (LOW-MEDIUM value)
UTILITY_PATTERNS: List[Tuple[re.Pattern, float]] = [
    # Layout utilities
    (re.compile(r'^(flex|grid|block|inline|hidden)$', re.I), 0.5),
    (re.compile(r'^(relative|absolute|fixed|sticky)$', re.I), 0.45),

    # Spacing - Tailwind style
    (re.compile(r'^[mp][trblxy]?-\d+$', re.I), 0.4),  # m-4, px-2, pt-8
    (re.compile(r'^gap-\d+$', re.I), 0.4),
    (re.compile(r'^space-[xy]-\d+$', re.I), 0.4),

    # Sizing
    (re.compile(r'^[wh]-\d+$', re.I), 0.4),  # w-full, h-screen
    (re.compile(r'^(min|max)-[wh]-', re.I), 0.4),

    # Typography
    (re.compile(r'^text-(xs|sm|base|lg|xl|2xl|3xl)', re.I), 0.45),
    (re.compile(r'^font-(thin|light|normal|medium|semibold|bold)', re.I), 0.45),
    (re.compile(r'^(leading|tracking)-', re.I), 0.4),

    # Colors
    (re.compile(r'^(text|bg|border)-(black|white|gray|red|blue|green)', re.I), 0.45),
    (re.compile(r'^(text|bg|border)-\w+-\d{2,3}$', re.I), 0.4),  # bg-blue-500

    # Borders/Rounded
    (re.compile(r'^(border|rounded)(-\w+)?$', re.I), 0.4),
    (re.compile(r'^shadow(-\w+)?$', re.I), 0.4),

    # Flexbox/Grid utilities
    (re.compile(r'^(justify|items|content|self)-(start|end|center)', re.I), 0.45),
    (re.compile(r'^(flex|grid)-(row|col|wrap)', re.I), 0.45),

    # Responsive prefixes
    (re.compile(r'^(sm|md|lg|xl|2xl):', re.I), 0.4),
]

# Framework patterns - Component libraries (MEDIUM value)
FRAMEWORK_PATTERNS: List[Tuple[re.Pattern, float]] = [
    # Material UI
    (re.compile(r'^Mui[A-Z]', re.I), 0.55),
    (re.compile(r'^MuiButton|MuiInput|MuiCard', re.I), 0.6),

    # Chakra UI
    (re.compile(r'^chakra-', re.I), 0.55),

    # Ant Design
    (re.compile(r'^ant-', re.I), 0.55),

    # Bootstrap
    (re.compile(r'^(btn|col|row|container|navbar)-', re.I), 0.5),
    (re.compile(r'^(d|m|p|g)-\d+$', re.I), 0.45),  # d-flex, m-3

    # Bulma
    (re.compile(r'^(is|has)-(primary|info|success|warning|danger)', re.I), 0.5),

    # Foundation
    (re.compile(r'^(small|medium|large)-\d+$', re.I), 0.45),
]

# Hash/Generated patterns - Usually removable (LOW value)
HASH_PATTERNS: List[Tuple[re.Pattern, float]] = [
    # styled-components
    (re.compile(r'^css-[a-z0-9]+$', re.I), 0.1),
    (re.compile(r'^sc-[a-zA-Z]+[a-zA-Z0-9]*$', re.I), 0.1),

    # CSS Modules
    (re.compile(r'^_[a-zA-Z0-9]{4,}$'), 0.1),
    (re.compile(r'__[a-zA-Z0-9]{4,}$'), 0.1),
    (re.compile(r'^[a-zA-Z]+_[a-zA-Z0-9]{5,}$'), 0.15),  # Component_abc123

    # Emotion
    (re.compile(r'^css-[a-z0-9]+-[a-zA-Z]+$', re.I), 0.1),

    # Material UI JSS
    (re.compile(r'^jss-\d+$', re.I), 0.1),
    (re.compile(r'^makeStyles-[a-zA-Z]+-\d+$', re.I), 0.1),

    # Pure hash classes
    (re.compile(r'^[a-f0-9]{6,}$', re.I), 0.0),
    (re.compile(r'^[a-z]{1,2}[a-f0-9]{4,}$', re.I), 0.05),

    # Webpack/Build tool generated
    (re.compile(r'^[a-zA-Z]+--[a-zA-Z0-9]+$'), 0.15),  # BEM-like but hashed
    (re.compile(r'___[a-zA-Z0-9]+$'), 0.1),
]


# =============================================================================
# Class Scorer
# =============================================================================

class ClassSemanticScorer:
    """Score CSS classes for semantic relevance.

    Example:
        scorer = ClassSemanticScorer()

        # Score single class
        result = scorer.score("product-card")
        print(f"{result.class_name}: {result.score:.2f} ({result.category.value})")

        # Filter classes
        classes = ["product-card", "css-abc123", "flex", "p-4"]
        kept = scorer.filter_classes(classes, threshold=0.3)
        # Result: ["product-card", "flex"]
    """

    def __init__(
        self,
        semantic_weight: float = 1.0,
        utility_weight: float = 0.8,
        hash_penalty: float = 0.5,
    ):
        """Initialize scorer.

        Args:
            semantic_weight: Multiplier for semantic class scores.
            utility_weight: Multiplier for utility class scores.
            hash_penalty: Penalty multiplier for hash classes.
        """
        self.semantic_weight = semantic_weight
        self.utility_weight = utility_weight
        self.hash_penalty = hash_penalty

    def score(self, class_name: str) -> ClassScore:
        """Score a single CSS class.

        Args:
            class_name: CSS class name to score.

        Returns:
            ClassScore with score, category, and keep recommendation.
        """
        if not class_name or not class_name.strip():
            return ClassScore(
                class_name=class_name,
                score=0.0,
                category=ClassCategory.UNKNOWN,
                keep=False,
            )

        class_name = class_name.strip()

        # Check patterns in order of priority
        category, base_score = self._match_patterns(class_name)

        # Apply weights
        if category == ClassCategory.SEMANTIC:
            final_score = base_score * self.semantic_weight
        elif category == ClassCategory.UTILITY:
            final_score = base_score * self.utility_weight
        elif category == ClassCategory.HASH:
            final_score = base_score * self.hash_penalty
        else:
            final_score = base_score

        final_score = min(1.0, max(0.0, final_score))

        return ClassScore(
            class_name=class_name,
            score=final_score,
            category=category,
            keep=final_score >= 0.3,  # Default threshold
        )

    def _match_patterns(self, class_name: str) -> Tuple[ClassCategory, float]:
        """Match class against all pattern categories.

        Args:
            class_name: CSS class name.

        Returns:
            Tuple of (category, score).
        """
        # Check hash patterns first (quick rejection)
        for pattern, score in HASH_PATTERNS:
            if pattern.match(class_name):
                return ClassCategory.HASH, score

        # Check semantic patterns (highest value)
        for pattern, score in SEMANTIC_PATTERNS:
            if pattern.search(class_name):
                return ClassCategory.SEMANTIC, score

        # Check structural patterns
        for pattern, score in STRUCTURAL_PATTERNS:
            if pattern.search(class_name):
                return ClassCategory.STRUCTURAL, score

        # Check interactive patterns
        for pattern, score in INTERACTIVE_PATTERNS:
            if pattern.search(class_name):
                return ClassCategory.INTERACTIVE, score

        # Check framework patterns
        for pattern, score in FRAMEWORK_PATTERNS:
            if pattern.search(class_name):
                return ClassCategory.FRAMEWORK, score

        # Check utility patterns
        for pattern, score in UTILITY_PATTERNS:
            if pattern.search(class_name):
                return ClassCategory.UTILITY, score

        # Unknown - give moderate score if looks meaningful
        if len(class_name) > 3 and '-' in class_name:
            return ClassCategory.UNKNOWN, 0.4
        elif len(class_name) > 5:
            return ClassCategory.UNKNOWN, 0.3

        return ClassCategory.UNKNOWN, 0.2

    def filter_classes(
        self,
        classes: List[str],
        threshold: float = 0.3,
    ) -> List[str]:
        """Filter classes by score threshold.

        Args:
            classes: List of CSS class names.
            threshold: Minimum score to keep (0.0 to 1.0).

        Returns:
            List of classes that meet the threshold.
        """
        result = []
        for class_name in classes:
            score_result = self.score(class_name)
            if score_result.score >= threshold:
                result.append(class_name)
        return result

    def score_all(self, classes: List[str]) -> List[ClassScore]:
        """Score all classes and return detailed results.

        Args:
            classes: List of CSS class names.

        Returns:
            List of ClassScore objects.
        """
        return [self.score(cls) for cls in classes]


# =============================================================================
# Convenience Functions
# =============================================================================

# Default scorer instance
_default_scorer = ClassSemanticScorer()


def score_class(class_name: str) -> float:
    """Score a CSS class for semantic relevance (convenience function).

    Args:
        class_name: CSS class name.

    Returns:
        Score from 0.0 to 1.0.
    """
    return _default_scorer.score(class_name).score


def filter_classes(classes: List[str], threshold: float = 0.3) -> List[str]:
    """Filter CSS classes by score (convenience function).

    Args:
        classes: List of CSS class names.
        threshold: Minimum score to keep.

    Returns:
        Filtered list of classes.
    """
    return _default_scorer.filter_classes(classes, threshold)


def clean_classes(class_string: str, threshold: float = 0.3) -> str:
    """Clean a class attribute string (convenience function).

    Args:
        class_string: Space-separated class names (like HTML class attribute).
        threshold: Minimum score to keep.

    Returns:
        Cleaned class string.
    """
    classes = class_string.split()
    kept = filter_classes(classes, threshold)
    return ' '.join(kept)
