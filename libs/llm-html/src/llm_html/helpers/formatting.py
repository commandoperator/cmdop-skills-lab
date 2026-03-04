"""JSON formatting utilities."""

from __future__ import annotations

from toon import encode as toon_encode


def json_to_toon(data: dict | list) -> str:
    """
    Convert JSON to TOON format (saves 30-50% tokens).

    Example:
        {"name": "Alice", "age": 25} → "name: Alice\\nage: 25"
    """
    return toon_encode(data)
