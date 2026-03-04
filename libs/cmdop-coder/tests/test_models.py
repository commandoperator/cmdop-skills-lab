"""Tests for Pydantic data models."""

from cmdop_coder._models import (
    AnalyzeResult,
    FunctionInfo,
    FunctionsResult,
    OutlineItem,
    OutlineResult,
    SymbolMatch,
    SymbolsResult,
)


class TestFunctionInfo:
    def test_fields(self) -> None:
        fn = FunctionInfo(line=10, name="my_func", signature="def my_func(x: int) -> str:")
        assert fn.line == 10
        assert fn.name == "my_func"
        assert fn.signature == "def my_func(x: int) -> str:"

    def test_model_dump(self) -> None:
        fn = FunctionInfo(line=1, name="f", signature="def f():")
        d = fn.model_dump()
        assert d == {"line": 1, "name": "f", "signature": "def f():"}


class TestFunctionsResult:
    def test_empty(self) -> None:
        r = FunctionsResult(file="x.py", language="python", count=0, functions=[])
        assert r.count == 0
        assert r.functions == []

    def test_with_functions(self) -> None:
        fn = FunctionInfo(line=5, name="foo", signature="def foo():")
        r = FunctionsResult(file="a.py", language="python", count=1, functions=[fn])
        assert r.count == 1
        assert r.functions[0].name == "foo"

    def test_model_dump_roundtrip(self) -> None:
        fn = FunctionInfo(line=3, name="bar", signature="async def bar():")
        r = FunctionsResult(file="b.py", language="python", count=1, functions=[fn])
        d = r.model_dump()
        assert d["language"] == "python"
        assert d["functions"][0]["name"] == "bar"


class TestSymbolsResult:
    def test_empty(self) -> None:
        r = SymbolsResult(symbol="Foo", count=0, matches=[])
        assert r.count == 0

    def test_with_matches(self) -> None:
        m = SymbolMatch(file="a.py", line=7, text="class Foo:")
        r = SymbolsResult(symbol="Foo", count=1, matches=[m])
        assert r.matches[0].line == 7
        assert r.matches[0].text == "class Foo:"

    def test_model_dump(self) -> None:
        r = SymbolsResult(symbol="X", count=0, matches=[])
        d = r.model_dump()
        assert d["symbol"] == "X"
        assert d["matches"] == []


class TestOutlineResult:
    def test_fields(self) -> None:
        item = OutlineItem(line=1, type="import_statement", name="os")
        r = OutlineResult(file="m.py", language="python", count=1, outline=[item])
        assert r.outline[0].type == "import_statement"
        assert r.outline[0].name == "os"


class TestAnalyzeResult:
    def test_defaults(self) -> None:
        r = AnalyzeResult(
            file="f.py",
            language="python",
            extension=".py",
            size_bytes=100,
            total_lines=10,
            code_lines=8,
            blank_lines=1,
            comment_lines=1,
        )
        assert r.function_count is None

    def test_with_function_count(self) -> None:
        r = AnalyzeResult(
            file="f.py",
            language="python",
            extension=".py",
            size_bytes=200,
            total_lines=20,
            code_lines=15,
            blank_lines=3,
            comment_lines=2,
            function_count=4,
        )
        assert r.function_count == 4

    def test_model_dump(self) -> None:
        r = AnalyzeResult(
            file="f.go",
            language="go",
            extension=".go",
            size_bytes=50,
            total_lines=5,
            code_lines=4,
            blank_lines=1,
            comment_lines=0,
            function_count=1,
        )
        d = r.model_dump()
        assert d["language"] == "go"
        assert d["function_count"] == 1
