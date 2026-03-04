"""Tree-sitter parser utilities."""

from __future__ import annotations

from pathlib import Path

# Language detection by file extension
_EXT_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".cs": "c_sharp",
    ".css": "css",
    ".html": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".lua": "lua",
    ".r": "r",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
    ".elm": "elm",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".tf": "hcl",
}


def detect_language(path: str | Path) -> str | None:
    """Detect tree-sitter language name from file path."""
    p = Path(path)
    name = p.name.lower()
    if name == "dockerfile" or name.startswith("dockerfile."):
        return "dockerfile"
    return _EXT_TO_LANG.get(p.suffix.lower())


def get_parser(language: str) -> object:
    """Return a tree-sitter parser for the given language name."""
    try:
        from tree_sitter_language_pack import get_parser as _get_parser  # type: ignore[import]
        return _get_parser(language)
    except Exception as e:
        raise RuntimeError(f"Cannot load tree-sitter parser for {language!r}: {e}") from e


def parse_file(path: str | Path) -> tuple[object, bytes, str]:
    """Parse a source file, returning (tree, source_bytes, language)."""
    p = Path(path)
    lang = detect_language(p)
    if lang is None:
        raise ValueError(f"Unsupported file type: {p.suffix!r}")
    source = p.read_bytes()
    parser = get_parser(lang)
    tree = parser.parse(source)  # type: ignore[union-attr]
    return tree, source, lang
