from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Category


@dataclass
class PreferenceMemory:
    important_domains: set[str] = field(default_factory=set)
    cleanup_domains: set[str] = field(default_factory=set)
    ignored_domains: set[str] = field(default_factory=set)
    category_overrides: dict[str, Category] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "PreferenceMemory":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            important_domains=set(data.get("important_domains", [])),
            cleanup_domains=set(data.get("cleanup_domains", [])),
            ignored_domains=set(data.get("ignored_domains", [])),
            category_overrides={
                key: Category(value)
                for key, value in data.get("category_overrides", {}).items()
                if value in Category._value2member_map_
            },
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "important_domains": sorted(self.important_domains),
            "cleanup_domains": sorted(self.cleanup_domains),
            "ignored_domains": sorted(self.ignored_domains),
            "category_overrides": {
                key: category.value for key, category in sorted(self.category_overrides.items())
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "important_domains": sorted(self.important_domains),
            "cleanup_domains": sorted(self.cleanup_domains),
            "ignored_domains": sorted(self.ignored_domains),
            "category_overrides": {
                key: category.value for key, category in self.category_overrides.items()
            },
        }
