# cmdop-coder

Code analysis skill using tree-sitter AST parsing. Supports 40+ languages.

## Commands

- `functions --path <FILE>` — extract function/method signatures with line numbers
- `symbols --symbol <NAME> [--path <DIR>]` — find all occurrences of a symbol
- `outline --path <FILE>` — structural outline (imports, classes, functions, types)
- `analyze --path <FILE>` — file statistics (lines, complexity, language)

## Usage

```
cmdop-coder functions --path src/main.py
cmdop-coder symbols --symbol MyClass --path ./src
cmdop-coder outline --path internal/agent/core/agent.go
cmdop-coder analyze --path package.json
```

## Supported Languages

Go, Python, JavaScript, TypeScript, Rust, Java, C, C++, Ruby, PHP, Swift,
Kotlin, C#, CSS, HTML, JSON, YAML, TOML, Bash, SQL, and more.
