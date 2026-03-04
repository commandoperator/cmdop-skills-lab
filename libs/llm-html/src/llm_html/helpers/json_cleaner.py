"""JSON cleaning utilities for LLM consumption."""

from __future__ import annotations

from typing import Any

from toon import encode as toon_encode


class JsonCleaner:
    """
    Clean JSON and convert to TOON format for LLM.

    Usage:
        cleaner = JsonCleaner(noise_keys={"Photos", "images"})
        toon_text = cleaner.to_toon(data)
    """

    DEFAULT_NOISE_KEYS = frozenset({
        "statusItemTypes",
        "attributes",
        "ordering",
        "updatedDate",
    })

    def __init__(self, noise_keys: set[str] | None = None):
        self.noise_keys = self.DEFAULT_NOISE_KEYS | (noise_keys or set())

    def compact(self, data: Any) -> Any:
        """Remove nulls, empty values, noise keys. Simplify {code,title}->title."""
        def _process(obj: Any) -> Any:
            if isinstance(obj, dict):
                # Simplify {code, title} pattern
                keys = set(obj.keys())
                if keys <= {"code", "title", "description"} and "title" in keys:
                    return obj.get("title") or obj.get("code")
                # Clean dict
                result = {}
                for k, v in obj.items():
                    if k in self.noise_keys:
                        continue
                    cleaned = _process(v)
                    if cleaned is not None and cleaned != "" and cleaned != [] and cleaned != {}:
                        result[k] = cleaned
                return result
            elif isinstance(obj, list):
                return [_process(item) for item in obj if _process(item) not in (None, "", [], {})]
            return obj
        return _process(data)

    def to_toon(self, data: Any) -> str:
        """Compact and convert to TOON format."""
        return toon_encode(self.compact(data))
