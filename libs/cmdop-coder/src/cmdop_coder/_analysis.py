"""Code analysis functions using tree-sitter AST."""

from __future__ import annotations

from pathlib import Path

from ._models import (
    AnalyzeResult,
    FunctionInfo,
    FunctionsResult,
    OutlineItem,
    OutlineResult,
    SymbolMatch,
    SymbolsResult,
)
from ._parser import detect_language, parse_file

# Node types that represent function/method definitions per language
_FUNCTION_NODES: dict[str, list[str]] = {
    "python":     ["function_definition", "async_function_definition"],
    "javascript": ["function_declaration", "arrow_function", "method_definition", "function_expression"],
    "typescript": ["function_declaration", "arrow_function", "method_definition", "function_expression"],
    "tsx":        ["function_declaration", "arrow_function", "method_definition", "function_expression"],
    "go":         ["function_declaration", "method_declaration"],
    "rust":       ["function_item"],
    "java":       ["method_declaration", "constructor_declaration"],
    "c":          ["function_definition"],
    "cpp":        ["function_definition"],
    "ruby":       ["method", "singleton_method"],
    "php":        ["function_definition", "method_declaration"],
    "swift":      ["function_declaration"],
    "kotlin":     ["function_declaration"],
    "c_sharp":    ["method_declaration", "constructor_declaration"],
    "lua":        ["function_definition", "local_function"],
    "scala":      ["function_definition"],
    "elixir":     ["def", "defp"],
}

# Node types for outline (structural elements) per language
_OUTLINE_NODES: dict[str, list[str]] = {
    "python":     ["import_statement", "import_from_statement", "class_definition",
                   "function_definition", "async_function_definition"],
    "javascript": ["import_declaration", "class_declaration", "function_declaration",
                   "lexical_declaration", "variable_declaration"],
    "typescript": ["import_declaration", "class_declaration", "function_declaration",
                   "interface_declaration", "type_alias_declaration", "enum_declaration"],
    "tsx":        ["import_declaration", "class_declaration", "function_declaration",
                   "interface_declaration", "type_alias_declaration"],
    "go":         ["import_declaration", "type_declaration", "function_declaration",
                   "method_declaration", "var_declaration", "const_declaration"],
    "rust":       ["use_declaration", "struct_item", "enum_item", "function_item",
                   "impl_item", "trait_item", "mod_item"],
    "java":       ["import_declaration", "class_declaration", "interface_declaration",
                   "method_declaration"],
    "c":          ["preproc_include", "struct_specifier", "function_definition", "type_definition"],
    "cpp":        ["preproc_include", "class_specifier", "struct_specifier",
                   "function_definition", "namespace_definition"],
}

_IDENTIFIER_TYPES = frozenset({
    "identifier", "name", "property_identifier",
    "type_identifier", "field_identifier",
})


def _node_name(node: object, source: bytes) -> str:
    """Extract the name identifier text from an AST node."""
    for child in node.children:  # type: ignore[union-attr]
        if child.type in _IDENTIFIER_TYPES:
            return source[child.start_byte:child.end_byte].decode(errors="replace")
    raw = source[node.start_byte:node.start_byte + 60]  # type: ignore[union-attr]
    return raw.decode(errors="replace").split("\n")[0]


def _collect_nodes(node: object, types: frozenset[str], depth: int = 0, max_depth: int = 20) -> list[object]:
    """Walk AST and collect nodes matching the given types."""
    if depth > max_depth:
        return []
    results: list[object] = []
    if node.type in types:  # type: ignore[union-attr]
        results.append(node)
    for child in node.children:  # type: ignore[union-attr]
        results.extend(_collect_nodes(child, types, depth + 1, max_depth))
    return results


def _first_line(node: object, source: bytes) -> str:
    """Return the first line of a node's source text, truncated to 120 chars."""
    raw = source[node.start_byte:node.end_byte]  # type: ignore[union-attr]
    return raw.decode(errors="replace").split("\n")[0][:120]


def extract_functions(path: str | Path) -> FunctionsResult:
    """Extract function/method signatures with line numbers from a source file."""
    tree, source, lang = parse_file(path)
    types = frozenset(_FUNCTION_NODES.get(lang, ["function_definition", "function_declaration"]))
    nodes = _collect_nodes(tree.root_node, types)  # type: ignore[union-attr]

    functions = [
        FunctionInfo(
            line=node.start_point[0] + 1,  # type: ignore[union-attr]
            name=_node_name(node, source),
            signature=_first_line(node, source),
        )
        for node in nodes
    ]
    return FunctionsResult(file=str(path), language=lang, count=len(functions), functions=functions)


def find_symbol(symbol: str, path: str | Path = ".") -> SymbolsResult:
    """Find all occurrences of a symbol across source files."""
    p = Path(path)
    candidates = [p] if p.is_file() else list(p.rglob("*"))
    matches: list[SymbolMatch] = []

    for f in candidates:
        if not f.is_file() or detect_language(f) is None:
            continue
        try:
            lines = f.read_bytes().decode(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            if symbol in line:
                matches.append(SymbolMatch(file=str(f), line=i, text=line.strip()))

    return SymbolsResult(symbol=symbol, count=len(matches), matches=matches)


def get_outline(path: str | Path) -> OutlineResult:
    """Get structural outline of a source file (imports, classes, functions, types)."""
    tree, source, lang = parse_file(path)
    types = frozenset(_OUTLINE_NODES.get(lang, []))

    if not types:
        items = _fallback_outline(tree.root_node, source)  # type: ignore[union-attr]
        return OutlineResult(file=str(path), language=lang, count=len(items), outline=items)

    nodes = _collect_nodes(tree.root_node, types, max_depth=3)  # type: ignore[union-attr]
    items = [
        OutlineItem(
            line=node.start_point[0] + 1,  # type: ignore[union-attr]
            type=node.type,  # type: ignore[union-attr]
            name=_node_name(node, source),
        )
        for node in nodes
    ]
    return OutlineResult(file=str(path), language=lang, count=len(items), outline=items)


def _fallback_outline(root: object, source: bytes) -> list[OutlineItem]:
    """Return top-level nodes as outline when language has no specific config."""
    return [
        OutlineItem(
            line=child.start_point[0] + 1,  # type: ignore[union-attr]
            type=child.type,  # type: ignore[union-attr]
            name=_first_line(child, source)[:60],
        )
        for child in root.children  # type: ignore[union-attr]
    ]


def analyze_file(path: str | Path) -> AnalyzeResult:
    """Analyze a source file: language detection, line counts, function count."""
    p = Path(path)
    source = p.read_bytes()
    lang = detect_language(p)
    lines = source.decode(errors="replace").splitlines()

    blank = sum(1 for ln in lines if not ln.strip())
    comment = sum(1 for ln in lines if ln.strip().startswith(("#", "//", "/*", "*")))
    code = len(lines) - blank - comment

    function_count: int | None = None
    if lang and lang in _FUNCTION_NODES:
        try:
            function_count = extract_functions(p).count
        except Exception:
            pass

    return AnalyzeResult(
        file=str(p),
        language=lang or "unknown",
        extension=p.suffix,
        size_bytes=len(source),
        total_lines=len(lines),
        code_lines=code,
        blank_lines=blank,
        comment_lines=comment,
        function_count=function_count,
    )
