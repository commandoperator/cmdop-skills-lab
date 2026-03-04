"""Data models for cmdop-coder results."""

from pydantic import BaseModel


class FunctionInfo(BaseModel):
    """A single function or method extracted from source code."""

    line: int
    name: str
    signature: str


class FunctionsResult(BaseModel):
    """Result of extracting functions from a file."""

    file: str
    language: str
    count: int
    functions: list[FunctionInfo]


class SymbolMatch(BaseModel):
    """A single occurrence of a symbol in source code."""

    file: str
    line: int
    text: str


class SymbolsResult(BaseModel):
    """Result of searching for a symbol across files."""

    symbol: str
    count: int
    matches: list[SymbolMatch]


class OutlineItem(BaseModel):
    """A structural element in a source file outline."""

    line: int
    type: str
    name: str


class OutlineResult(BaseModel):
    """Result of generating a structural outline for a file."""

    file: str
    language: str
    count: int
    outline: list[OutlineItem]


class AnalyzeResult(BaseModel):
    """Statistics for a source file."""

    file: str
    language: str
    extension: str
    size_bytes: int
    total_lines: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    function_count: int | None = None
