"""cmdop-coder CMDOP skill — code analysis with tree-sitter AST."""

from cmdop_skill import Arg, Skill

from cmdop_coder._analysis import analyze_file, extract_functions, find_symbol, get_outline

skill = Skill()


@skill.command
def functions(
    path: str = Arg(help="Path to source file", required=True),
) -> dict:
    """Extract function/method signatures with line numbers."""
    return extract_functions(path).model_dump()


@skill.command
def symbols(
    symbol: str = Arg(help="Symbol name to find", required=True),
    path: str = Arg("--path", default=".", help="File or directory to search (default: current dir)"),
) -> dict:
    """Find all occurrences of a symbol across source files."""
    return find_symbol(symbol, path).model_dump()


@skill.command
def outline(
    path: str = Arg(help="Path to source file", required=True),
) -> dict:
    """Get structural outline: imports, classes, functions, types."""
    return get_outline(path).model_dump()


@skill.command
def analyze(
    path: str = Arg(help="Path to source file", required=True),
) -> dict:
    """Analyze a file: language, line counts, function count."""
    return analyze_file(path).model_dump()


def main() -> None:
    """CLI entry point."""
    skill.run()
