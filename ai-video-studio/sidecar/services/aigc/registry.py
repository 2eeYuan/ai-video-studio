"""
AIGC adapter registry.
"""
from .base import AIGCAdapter
from .dreamina import DreaminaAdapter
from .kling import KlingAdapter
from .runway import RunwayAdapter
from .pika import PikaAdapter
from .luma import LumaAdapter


class AdapterRegistry:
    def __init__(self):
        self._adapters: dict[str, AIGCAdapter] = {}

    def register(self, adapter: AIGCAdapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> AIGCAdapter:
        if name not in self._adapters:
            raise KeyError(f"Adapter '{name}' not registered. Available: {list(self._adapters.keys())}")
        return self._adapters[name]

    def update_config(self, name: str, api_key: str = "", base_url: str = ""):
        """Update adapter config at runtime (called from API endpoint)."""
        adapter = self.get(name)
        if api_key:
            adapter.api_key = api_key
        if base_url:
            adapter.base_url = base_url

    @property
    def available(self) -> list[str]:
        return list(self._adapters.keys())


# Default registry — register all known adapters
registry = AdapterRegistry()
registry.register(DreaminaAdapter())
registry.register(KlingAdapter())
registry.register(RunwayAdapter())
registry.register(PikaAdapter())
registry.register(LumaAdapter())
