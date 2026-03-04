# llm-html

LLM-optimized HTML cleaning with hydration extraction, token budgets, and multiple output formats.

## Quick Start

```python
from llm_html import HTMLCleaner, CleanerConfig, OutputFormat

# Basic usage
cleaner = HTMLCleaner()
result = cleaner.clean(html)

# With hydration extraction (Next.js, Nuxt, etc.)
if result.hydration_data:
    products = result.hydration_data.get("products", [])
else:
    cleaned = result.html

# Custom configuration
config = CleanerConfig(
    max_tokens=5000,
    output_format=OutputFormat.MARKDOWN,
    filter_classes=True,
)
cleaner = HTMLCleaner(config)
result = cleaner.clean(html)
```

## Features

- Hydration-first: extract SSR data (Next.js, Nuxt, etc.) before DOM parsing
- Token budget targeting with adaptive D2Snap downsampling
- Multiple output formats: HTML, Markdown, AOM YAML, XTree
- Shadow DOM flattening for Web Components
- Semantic chunking for large pages
- CSS class filtering with semantic scoring
- Detailed statistics (reduction, timing, element counts)

## Output Formats

| Format | Use case |
|---|---|
| `HTML` | Default cleaned HTML |
| `MARKDOWN` | LLM-friendly text |
| `AOM` | Playwright-style accessibility tree |
| `XTREE` | Compact element tree |

## Environment Variables

No environment variables required.
