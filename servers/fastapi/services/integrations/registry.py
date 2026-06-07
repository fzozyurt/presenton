from __future__ import annotations

import logging

from services.integrations.ports import DataAdapterPort, DataAdapterRegistryPort
from services.integrations.dto import ResolvedAdapterConfig, NormalizedDataSetDTO

LOGGER = logging.getLogger(__name__)


class StaticDataAdapterRegistry:
    def __init__(self, adapters: list[DataAdapterPort] | None = None):
        self._adapters: dict[str, DataAdapterPort] = {}
        if adapters:
            for adapter in adapters:
                self.register(adapter)

    def register(self, adapter: DataAdapterPort) -> None:
        key = adapter.adapter_type.lower()
        if key in self._adapters:
            LOGGER.warning("Adapter type %r is already registered; overwriting.", key)
        self._adapters[key] = adapter
        LOGGER.info("Registered data adapter: %s", key)

    def get(self, adapter_type: str) -> DataAdapterPort:
        key = adapter_type.lower()
        if key not in self._adapters:
            available = list(self._adapters.keys())
            raise KeyError(f"No adapter registered for type {adapter_type!r}. Available: {available}")
        return self._adapters[key]

    def list_types(self) -> list[str]:
        return list(self._adapters.keys())


_registry: StaticDataAdapterRegistry | None = None


def get_adapter_registry() -> StaticDataAdapterRegistry:
    global _registry
    if _registry is None:
        _registry = StaticDataAdapterRegistry()
    return _registry
