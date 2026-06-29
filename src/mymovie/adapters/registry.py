from __future__ import annotations

from mymovie.adapters.base import AIGCAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, AIGCAdapter] = {}

    def register(self, adapter: AIGCAdapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> AIGCAdapter:
        if name not in self._adapters:
            raise KeyError(f"AIGC adapter '{name}' not registered. Available: {list(self._adapters.keys())}")
        return self._adapters[name]

    def default(self) -> AIGCAdapter:
        if not self._adapters:
            raise RuntimeError("No AIGC adapters registered")
        return next(iter(self._adapters.values()))

    @property
    def available(self) -> list[str]:
        return list(self._adapters.keys())
