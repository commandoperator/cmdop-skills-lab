"""CSS framework detection patterns.

Detects CSS frameworks and libraries used in HTML for
optimized class handling.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Set


class CSSFramework(Enum):
    """Detected CSS framework."""

    UNKNOWN = "unknown"
    TAILWIND = "tailwind"
    BOOTSTRAP = "bootstrap"
    MATERIAL_UI = "material_ui"
    CHAKRA_UI = "chakra_ui"
    ANT_DESIGN = "ant_design"
    BULMA = "bulma"
    FOUNDATION = "foundation"
    STYLED_COMPONENTS = "styled_components"
    EMOTION = "emotion"
    CSS_MODULES = "css_modules"


@dataclass
class FrameworkDetection:
    """Result of CSS framework detection."""

    framework: CSSFramework
    """Primary detected framework."""

    confidence: float
    """Detection confidence (0.0 to 1.0)."""

    signals: List[str]
    """Detected signals that led to this conclusion."""

    secondary: List[CSSFramework]
    """Other frameworks that may also be present."""


# =============================================================================
# Detection Patterns
# =============================================================================

# Tailwind CSS patterns
TAILWIND_PATTERNS = [
    re.compile(r'\b(flex|grid|block|inline-block|hidden)\b'),
    re.compile(r'\b[mp][trblxy]?-\d+\b'),  # m-4, px-2
    re.compile(r'\btext-(xs|sm|base|lg|xl|2xl|3xl)\b'),
    re.compile(r'\b(bg|text|border)-(gray|red|blue|green)-\d{2,3}\b'),
    re.compile(r'\b(justify|items|content)-(start|end|center|between)\b'),
    re.compile(r'\brounded(-\w+)?\b'),
    re.compile(r'\bshadow(-\w+)?\b'),
    re.compile(r'\b(sm|md|lg|xl|2xl):'),  # Responsive prefixes
]

# Bootstrap patterns
BOOTSTRAP_PATTERNS = [
    re.compile(r'\bcol-(xs|sm|md|lg|xl)-\d+\b'),
    re.compile(r'\bbtn-(primary|secondary|success|danger|warning|info)\b'),
    re.compile(r'\b(container|row|col)\b'),
    re.compile(r'\bnavbar(-\w+)?\b'),
    re.compile(r'\bcard(-\w+)?\b'),
    re.compile(r'\bmodal(-\w+)?\b'),
    re.compile(r'\b[dmp]-\d+\b'),  # d-flex, m-3
    re.compile(r'\bform-(control|group|check)\b'),
]

# Material UI patterns
MATERIAL_UI_PATTERNS = [
    re.compile(r'\bMui[A-Z][a-zA-Z]+\b'),
    re.compile(r'\bMuiButton-\w+\b'),
    re.compile(r'\bMuiTypography-\w+\b'),
    re.compile(r'\bMuiPaper-\w+\b'),
    re.compile(r'\bmakeStyles-\w+\b'),
    re.compile(r'\bjss-\d+\b'),
]

# Chakra UI patterns
CHAKRA_UI_PATTERNS = [
    re.compile(r'\bchakra-\w+\b'),
    re.compile(r'\bcss-[a-z0-9]+-chakra\b'),
]

# Ant Design patterns
ANT_DESIGN_PATTERNS = [
    re.compile(r'\bant-\w+\b'),
    re.compile(r'\bantd-\w+\b'),
    re.compile(r'\bant-(btn|input|form|table|modal)\b'),
]

# Bulma patterns
BULMA_PATTERNS = [
    re.compile(r'\b(is|has)-(primary|info|success|warning|danger|light|dark)\b'),
    re.compile(r'\bcolumns?\b'),
    re.compile(r'\b(hero|section|container|level)\b'),
    re.compile(r'\bbutton\s+is-\w+\b'),
]

# Foundation patterns
FOUNDATION_PATTERNS = [
    re.compile(r'\b(small|medium|large)-\d+\b'),
    re.compile(r'\bcell\b'),
    re.compile(r'\bgrid-(x|y|container)\b'),
    re.compile(r'\btop-bar\b'),
]

# styled-components patterns
STYLED_COMPONENTS_PATTERNS = [
    re.compile(r'\bsc-[a-zA-Z]+[a-zA-Z0-9]*\b'),
    re.compile(r'\bcss-[a-z0-9]{6,}\b'),
]

# Emotion patterns
EMOTION_PATTERNS = [
    re.compile(r'\bcss-[a-z0-9]+-[a-zA-Z]+\b'),
    re.compile(r'\bemotion-\d+\b'),
]

# CSS Modules patterns
CSS_MODULES_PATTERNS = [
    re.compile(r'\b[a-zA-Z]+_[a-zA-Z0-9]{5,}\b'),
    re.compile(r'\b_[a-zA-Z0-9]{6,}\b'),
    re.compile(r'___[a-zA-Z0-9]+\b'),
]


# =============================================================================
# Framework Detector
# =============================================================================

class FrameworkDetector:
    """Detect CSS frameworks from HTML class attributes.

    Example:
        detector = FrameworkDetector()

        # Detect from class list
        classes = ["flex", "p-4", "bg-blue-500", "rounded-lg"]
        result = detector.detect_from_classes(classes)
        print(f"Detected: {result.framework.value} ({result.confidence:.0%})")

        # Detect from HTML
        html = '<div class="MuiButton-root MuiButton-contained">Click</div>'
        result = detector.detect_from_html(html)
    """

    def detect_from_classes(self, classes: List[str]) -> FrameworkDetection:
        """Detect framework from list of class names.

        Args:
            classes: List of CSS class names.

        Returns:
            FrameworkDetection result.
        """
        class_string = ' '.join(classes)
        return self._detect(class_string)

    def detect_from_html(self, html: str) -> FrameworkDetection:
        """Detect framework from HTML string.

        Args:
            html: HTML string.

        Returns:
            FrameworkDetection result.
        """
        # Extract all class attributes
        class_pattern = re.compile(r'class=["\']([^"\']+)["\']', re.I)
        matches = class_pattern.findall(html)
        class_string = ' '.join(matches)
        return self._detect(class_string)

    def _detect(self, class_string: str) -> FrameworkDetection:
        """Internal detection logic.

        Args:
            class_string: Space-separated class names.

        Returns:
            FrameworkDetection result.
        """
        scores: dict[CSSFramework, int] = {fw: 0 for fw in CSSFramework}
        signals: dict[CSSFramework, List[str]] = {fw: [] for fw in CSSFramework}

        # Check each framework's patterns
        framework_patterns = [
            (CSSFramework.TAILWIND, TAILWIND_PATTERNS),
            (CSSFramework.BOOTSTRAP, BOOTSTRAP_PATTERNS),
            (CSSFramework.MATERIAL_UI, MATERIAL_UI_PATTERNS),
            (CSSFramework.CHAKRA_UI, CHAKRA_UI_PATTERNS),
            (CSSFramework.ANT_DESIGN, ANT_DESIGN_PATTERNS),
            (CSSFramework.BULMA, BULMA_PATTERNS),
            (CSSFramework.FOUNDATION, FOUNDATION_PATTERNS),
            (CSSFramework.STYLED_COMPONENTS, STYLED_COMPONENTS_PATTERNS),
            (CSSFramework.EMOTION, EMOTION_PATTERNS),
            (CSSFramework.CSS_MODULES, CSS_MODULES_PATTERNS),
        ]

        for framework, patterns in framework_patterns:
            for pattern in patterns:
                matches = pattern.findall(class_string)
                if matches:
                    scores[framework] += len(matches)
                    # Store first few matches as signals
                    if len(signals[framework]) < 3:
                        if isinstance(matches[0], tuple):
                            signals[framework].append(matches[0][0])
                        else:
                            signals[framework].append(matches[0])

        # Find primary framework
        max_score = max(scores.values())

        if max_score == 0:
            return FrameworkDetection(
                framework=CSSFramework.UNKNOWN,
                confidence=0.0,
                signals=[],
                secondary=[],
            )

        # Get primary and secondary frameworks
        sorted_frameworks = sorted(
            [(fw, score) for fw, score in scores.items() if score > 0],
            key=lambda x: x[1],
            reverse=True,
        )

        primary = sorted_frameworks[0][0]
        primary_score = sorted_frameworks[0][1]

        # Calculate confidence (normalized)
        total_signals = sum(scores.values())
        confidence = min(1.0, primary_score / max(5, total_signals * 0.5))

        # Get secondary frameworks
        secondary = [
            fw for fw, score in sorted_frameworks[1:]
            if score >= primary_score * 0.3  # At least 30% of primary
        ]

        return FrameworkDetection(
            framework=primary,
            confidence=confidence,
            signals=signals[primary],
            secondary=secondary,
        )

    def get_removable_patterns(
        self,
        framework: CSSFramework,
    ) -> List[re.Pattern]:
        """Get patterns for classes that can be removed for a framework.

        For CSS-in-JS frameworks like styled-components, the hash classes
        are usually safe to remove as they don't carry semantic meaning.

        Args:
            framework: Detected CSS framework.

        Returns:
            List of regex patterns for removable classes.
        """
        removable: dict[CSSFramework, List[re.Pattern]] = {
            CSSFramework.STYLED_COMPONENTS: [
                re.compile(r'^sc-[a-zA-Z]+[a-zA-Z0-9]*$'),
                re.compile(r'^css-[a-z0-9]+$'),
            ],
            CSSFramework.EMOTION: [
                re.compile(r'^css-[a-z0-9]+-[a-zA-Z]+$'),
            ],
            CSSFramework.CSS_MODULES: [
                re.compile(r'^_[a-zA-Z0-9]{6,}$'),
                re.compile(r'___[a-zA-Z0-9]+$'),
            ],
            CSSFramework.MATERIAL_UI: [
                re.compile(r'^jss-\d+$'),
                re.compile(r'^makeStyles-[a-zA-Z]+-\d+$'),
            ],
        }

        return removable.get(framework, [])


# =============================================================================
# Convenience Functions
# =============================================================================

_default_detector = FrameworkDetector()


def detect_css_framework(html_or_classes: str | List[str]) -> CSSFramework:
    """Detect CSS framework (convenience function).

    Args:
        html_or_classes: Either HTML string or list of class names.

    Returns:
        Detected CSSFramework enum value.
    """
    if isinstance(html_or_classes, list):
        result = _default_detector.detect_from_classes(html_or_classes)
    else:
        result = _default_detector.detect_from_html(html_or_classes)

    return result.framework
