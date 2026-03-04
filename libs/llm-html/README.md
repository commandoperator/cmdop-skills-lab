# llm-html

> **[CMDOP Skill](https://cmdop.com/skills/llm-html/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install llm-html
> ```
LLM-optimized HTML cleaning: hydration extraction, token budgets, multiple output formats.

## Install

```bash
pip install llm-html
```

## Quick Start

```python
from llm_html import HTMLCleaner, CleanerConfig, OutputFormat

# Basic cleaning
cleaner = HTMLCleaner()
result = cleaner.clean(html)
print(f"Reduction: {result.stats.reduction_percent}%")

# Hydration-first (extracts SSR data from Next.js, Nuxt, etc.)
if result.hydration_data:
    data = result.hydration_data
else:
    cleaned = result.html
```

## Convenience Functions

```python
from llm_html import clean, clean_to_json, clean_html, clean_for_llm

# Quick clean
result = clean(html)

# Get JSON if SSR data available, otherwise cleaned HTML
data = clean_to_json(html)

# Pipeline with full control
result = clean_html(html, max_tokens=5000)
result = clean_for_llm(html, output_format="markdown")
```

## Output Formats

```python
from llm_html import to_markdown, to_aom_yaml, to_xtree

md = to_markdown(html)
aom = to_aom_yaml(html)
xtree = to_xtree(html)
```

## Downsampling

Token-budget targeting with D2Snap algorithm:

```python
from llm_html import downsample_html, estimate_tokens

tokens = estimate_tokens(html)
if tokens > 10000:
    html = downsample_html(html, target_tokens=8000)
```

## Semantic Chunking

Split large pages into LLM-sized chunks:

```python
from llm_html import SemanticChunker, ChunkConfig

config = ChunkConfig(max_tokens=8000, max_items=20)
chunker = SemanticChunker(config)
result = chunker.chunk(soup)
for chunk in result.chunks:
    process(chunk.html)
```

## Shadow DOM

Flatten Web Components for LLM visibility:

```python
from llm_html import flatten_shadow_dom

flat = flatten_shadow_dom(html)
```

## Helpers

```python
from llm_html import html_to_text, extract_links, extract_images, json_to_toon

text = html_to_text(html)
links = extract_links(html, base_url="https://example.com")
images = extract_images(html)
toon = json_to_toon({"key": "value"})
```

## License

MIT
