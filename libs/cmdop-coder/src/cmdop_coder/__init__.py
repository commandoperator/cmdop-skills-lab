"""cmdop-coder — code analysis skill using tree-sitter AST parsing."""

from cmdop_coder._analysis import analyze_file, extract_functions, find_symbol, get_outline
from cmdop_coder._models import (
    AnalyzeResult,
    FunctionInfo,
    FunctionsResult,
    OutlineItem,
    OutlineResult,
    SymbolMatch,
    SymbolsResult,
)
from cmdop_coder._skill import skill

__all__ = [
    "AnalyzeResult",
    "FunctionInfo",
    "FunctionsResult",
    "OutlineItem",
    "OutlineResult",
    "SymbolMatch",
    "SymbolsResult",
    "analyze_file",
    "extract_functions",
    "find_symbol",
    "get_outline",
    "skill",
]
