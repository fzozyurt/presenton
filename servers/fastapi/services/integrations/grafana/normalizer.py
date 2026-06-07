from __future__ import annotations

from collections.abc import Mapping

from services.integrations.builder import NormalizedDataSetBuilder
from services.integrations.grafana.parser import GrafanaFrameParser
from services.integrations.dto import NormalizedDataSetDTO


class GrafanaResponseNormalizer:
    def __init__(self) -> None:
        self._parser = GrafanaFrameParser()
        self._builder = NormalizedDataSetBuilder()

    def normalize(
        self,
        raw: Mapping[str, object],
        *,
        source_id: str,
        binding_id: str | None = None,
        datasource_type: str = "grafana",
        preferred_data_kind: str | None = None,
        visualization_hint: str | None = None,
        row_limit: int | None = None,
    ) -> NormalizedDataSetDTO:
        frames = self._parser.parse(
            raw,
            source_id=source_id,
            source_type=datasource_type,
        )

        dataset = self._builder.build(
            frames,
            preferred_data_kind=preferred_data_kind,
            visualization_hint=visualization_hint,
            row_limit=row_limit,
        )

        if binding_id is not None:
            dataset.binding_id = binding_id
            dataset.metadata["binding_id"] = binding_id

        return dataset

__all__ = ["GrafanaResponseNormalizer"]
