"""Tests for core analysis functions."""

import textwrap
from pathlib import Path

from cmdop_coder._analysis import analyze_file, extract_functions, find_symbol, get_outline
from cmdop_coder._models import FunctionsResult, SymbolsResult, OutlineResult, AnalyzeResult


def src(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


class TestExtractFunctions:
    def test_python_def_async_and_method(self, tmp_path: Path) -> None:
        f = src(tmp_path, "sample.py", """\
            def hello(name: str) -> str:
                return f"hello {name}"

            async def fetch(url: str) -> bytes:
                pass

            class Foo:
                def method(self) -> None:
                    pass
        """)
        result = extract_functions(f)
        assert isinstance(result, FunctionsResult)
        assert result.language == "python"
        assert result.count == 3
        names = {fn.name for fn in result.functions}
        assert names == {"hello", "fetch", "method"}

    def test_python_line_numbers(self, tmp_path: Path) -> None:
        f = src(tmp_path, "lines.py", """\
            x = 1

            def first():
                pass

            def second():
                pass
        """)
        result = extract_functions(f)
        lines = [fn.line for fn in result.functions]
        assert lines == sorted(lines), "functions should be in source order"
        assert all(ln >= 1 for ln in lines)

    def test_go_func_and_method(self, tmp_path: Path) -> None:
        f = src(tmp_path, "main.go", """\
            package main

            func Add(a, b int) int { return a + b }

            func (s *Server) Start() error { return nil }
        """)
        result = extract_functions(f)
        assert result.language == "go"
        assert result.count >= 2

    def test_javascript_function_and_arrow(self, tmp_path: Path) -> None:
        f = src(tmp_path, "app.js", """\
            function greet(name) { return `Hello ${name}`; }
            const add = (a, b) => a + b;
        """)
        result = extract_functions(f)
        assert result.language == "javascript"
        assert result.count >= 1

    def test_no_functions_returns_empty(self, tmp_path: Path) -> None:
        f = src(tmp_path, "empty.py", "# comment\nx = 1\n")
        result = extract_functions(f)
        assert result.count == 0
        assert result.functions == []

    def test_signature_is_first_line(self, tmp_path: Path) -> None:
        f = src(tmp_path, "sig.py", """\
            def compute(x: int, y: int) -> int:
                return x + y
        """)
        result = extract_functions(f)
        assert result.count == 1
        assert result.functions[0].signature.startswith("def compute")


class TestFindSymbol:
    def test_multiple_occurrences_in_file(self, tmp_path: Path) -> None:
        f = src(tmp_path, "main.py", """\
            def my_func():
                pass

            x = my_func()
            y = my_func()
        """)
        result = find_symbol("my_func", f)
        assert isinstance(result, SymbolsResult)
        assert result.symbol == "my_func"
        assert result.count == 3

    def test_search_directory_multiple_files(self, tmp_path: Path) -> None:
        src(tmp_path, "a.py", "TARGET = 1\n")
        src(tmp_path, "b.py", "x = TARGET + 1\n")
        result = find_symbol("TARGET", tmp_path)
        assert result.count == 2

    def test_unsupported_files_skipped(self, tmp_path: Path) -> None:
        src(tmp_path, "a.py", "TARGET = 1\n")
        (tmp_path / "notes.txt").write_text("TARGET mentioned here\n")
        result = find_symbol("TARGET", tmp_path)
        # .txt has no language → skipped
        assert result.count == 1

    def test_symbol_not_found(self, tmp_path: Path) -> None:
        f = src(tmp_path, "main.py", "x = 1\n")
        result = find_symbol("NONEXISTENT", f)
        assert result.count == 0
        assert result.matches == []

    def test_match_contains_line_text(self, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", "def my_func(): pass\n")
        result = find_symbol("my_func", f)
        assert result.matches[0].text == "def my_func(): pass"
        assert result.matches[0].line == 1


class TestGetOutline:
    def test_python_imports_and_classes(self, tmp_path: Path) -> None:
        f = src(tmp_path, "mod.py", """\
            import os
            from pathlib import Path

            class MyClass:
                pass

            def top_level():
                pass
        """)
        result = get_outline(f)
        assert isinstance(result, OutlineResult)
        assert result.language == "python"
        assert result.count > 0
        types = {item.type for item in result.outline}
        assert any("import" in t for t in types)

    def test_go_outline_has_func(self, tmp_path: Path) -> None:
        f = src(tmp_path, "main.go", """\
            package main

            import "fmt"

            func main() { fmt.Println("hello") }
        """)
        result = get_outline(f)
        assert result.language == "go"
        assert result.count > 0

    def test_outline_items_have_line_numbers(self, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", """\
            import os
            class Foo: pass
        """)
        result = get_outline(f)
        assert all(item.line >= 1 for item in result.outline)


class TestAnalyzeFile:
    def test_python_basic_stats(self, tmp_path: Path) -> None:
        f = src(tmp_path, "script.py", """\
            # comment
            import os

            def main():
                x = 1

            main()
        """)
        result = analyze_file(f)
        assert isinstance(result, AnalyzeResult)
        assert result.language == "python"
        assert result.extension == ".py"
        assert result.total_lines > 0
        assert result.size_bytes > 0
        assert result.function_count == 1

    def test_line_counts_sum_to_total(self, tmp_path: Path) -> None:
        f = src(tmp_path, "x.py", """\
            # comment
            import os

            def foo():
                pass
        """)
        result = analyze_file(f)
        assert result.blank_lines + result.code_lines + result.comment_lines == result.total_lines

    def test_unknown_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "data.xyz"
        f.write_text("hello world\nline two\n")
        result = analyze_file(f)
        assert result.language == "unknown"
        assert result.total_lines == 2
        assert result.function_count is None

    def test_no_function_count_for_unsupported_lang(self, tmp_path: Path) -> None:
        f = src(tmp_path, "style.css", "body { margin: 0; }\n")
        result = analyze_file(f)
        # css not in _FUNCTION_NODES → function_count stays None
        assert result.function_count is None
