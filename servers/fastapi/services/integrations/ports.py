from __future__ import annotations

from typing import Protocol

from services.integrations.dto import (
    AnalysisResultDTO,
    NormalizedDataSetDTO,
    ResolvedAdapterConfig,
)


class DataAdapterPort(Protocol):
    @property
    def adapter_type(self) -> str: ...

    async def fetch_normalized(self, request: ResolvedAdapterConfig) -> NormalizedDataSetDTO: ...


class DataAdapterRegistryPort(Protocol):
    def get(self, adapter_type: str) -> DataAdapterPort: ...

    def list_types(self) -> list[str]: ...


class HttpClientPort(Protocol):
    async def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]: ...

    async def get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, object]: ...


class CredentialResolverPort(Protocol):
    async def resolve(self, credential_ref: str | None) -> dict[str, object] | None: ...


class DataAnalyzerPort(Protocol):
    async def analyze(
        self,
        dataset: NormalizedDataSetDTO,
        *,
        include_ml: bool = False,
    ) -> AnalysisResultDTO: ...
