from __future__ import annotations

from services.integrations.dto import ResolvedAdapterConfig, TimeRangeForFetch


class AdapterConfigResolver:
    @staticmethod
    def resolve(
        *,
        base_config: dict[str, object] | None = None,
        binding_config: dict[str, object] | None = None,
        query_config: dict[str, object] | None = None,
        runtime_params: dict[str, object] | None = None,
        datasource_id: str = "",
        datasource_type: str = "",
        binding_id: str | None = None,
        credential_ref: str | None = None,
        time_range: TimeRangeForFetch | None = None,
    ) -> ResolvedAdapterConfig:
        merged: dict[str, object] = {}
        if base_config:
            merged.update(base_config)
        if binding_config:
            merged.update(binding_config)
        if query_config:
            merged.update(query_config)
        if runtime_params:
            merged.update(runtime_params)

        return ResolvedAdapterConfig(
            datasource_id=datasource_id,
            datasource_type=datasource_type,
            binding_id=binding_id,
            credential_ref=credential_ref,
            config=merged,
            time_range=time_range,
        )
