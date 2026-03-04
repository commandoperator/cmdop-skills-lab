"""Tests for language detection and tree-sitter parsing."""

import pytest

from cmdop_coder._parser import detect_language, parse_file


class TestDetectLanguage:
    def test_python(self) -> None:
        assert detect_language("main.py") == "python"

    def test_typescript(self) -> None:
        assert detect_language("index.ts") == "typescript"

    def test_tsx(self) -> None:
        assert detect_language("App.tsx") == "tsx"

    def test_go(self) -> None:
        assert detect_language("main.go") == "go"

    def test_rust(self) -> None:
        assert detect_language("lib.rs") == "rust"

    def test_javascript(self) -> None:
        assert detect_language("app.js") == "javascript"
        assert detect_language("component.jsx") == "javascript"

    def test_c_variants(self) -> None:
        assert detect_language("main.c") == "c"
        assert detect_language("header.h") == "c"
        assert detect_language("app.cpp") == "cpp"

    def test_dockerfile(self) -> None:
        assert detect_language("Dockerfile") == "dockerfile"
        assert detect_language("Dockerfile.prod") == "dockerfile"

    def test_yaml_variants(self) -> None:
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_unknown_returns_none(self) -> None:
        assert detect_language("file.xyz") is None
        assert detect_language("README.md") is None
        assert detect_language("binary.bin") is None

    def test_case_insensitive_extension(self) -> None:
        assert detect_language("Main.PY") == "python"
        assert detect_language("App.TS") == "typescript"


class TestParseFile:
    def test_parse_python(self, tmp_path) -> None:
        f = tmp_path / "hello.py"
        f.write_text("def hello(): pass\n")
        tree, source, lang = parse_file(f)
        assert lang == "python"
        assert b"hello" in source
        assert tree is not None

    def test_parse_go(self, tmp_path) -> None:
        f = tmp_path / "main.go"
        f.write_text("package main\nfunc main() {}\n")
        tree, source, lang = parse_file(f)
        assert lang == "go"
        assert tree is not None

    def test_unsupported_extension_raises(self, tmp_path) -> None:
        f = tmp_path / "data.xyz"
        f.write_text("some content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_file(f)
