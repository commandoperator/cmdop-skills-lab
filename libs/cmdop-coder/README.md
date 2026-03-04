# cmdop-coder

> **[CMDOP Skill](https://cmdop.com/skills/cmdop-coder/)** — install and use via [CMDOP agent](https://cmdop.com):
> ```
> cmdop-skill install cmdop-coder
> ```

Code analysis using tree-sitter AST parsing. Extract functions, find symbols, get structural outlines. Supports 40+ languages.

## Install

```bash
pip install cmdop-coder
```

Or as a CMDOP skill:

```bash
cmdop-skill install path/to/cmdop-coder
```

## CLI

### Extract functions

```bash
cmdop-coder functions --path src/main.py
```

```json
{
  "file": "src/main.py",
  "language": "python",
  "count": 3,
  "functions": [
    {"line": 5, "name": "hello", "signature": "def hello(name: str) -> str:"},
    {"line": 9, "name": "fetch", "signature": "async def fetch(url: str) -> bytes:"}
  ]
}
```

### Find symbol

```bash
cmdop-coder symbols --symbol MyClass --path ./src
```

### Structural outline

```bash
cmdop-coder outline --path internal/agent/core/agent.go
```

### File statistics

```bash
cmdop-coder analyze --path service.py
```

## Python API

```python
from cmdop_coder import extract_functions, find_symbol, get_outline, analyze_file

# Extract all functions from a file
result = extract_functions("src/main.py")
for fn in result.functions:
    print(fn.line, fn.name, fn.signature)

# Find symbol across a directory
matches = find_symbol("MyClass", "./src")
for m in matches.matches:
    print(m.file, m.line, m.text)

# Structural outline
outline = get_outline("main.go")
for item in outline.outline:
    print(item.line, item.type, item.name)

# File statistics
stats = analyze_file("service.py")
print(stats.language, stats.total_lines, stats.function_count)
```

## Supported Languages

Go, Python, JavaScript, TypeScript, TSX, Rust, Java, C, C++, Ruby, PHP,
Swift, Kotlin, C#, CSS, HTML, JSON, YAML, TOML, Bash, SQL, Lua, Scala,
Elixir, Elm, Haskell, OCaml, HCL, Dockerfile and more.
