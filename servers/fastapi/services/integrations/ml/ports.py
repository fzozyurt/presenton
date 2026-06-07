from __future__ import annotations

import math
import statistics as _statistics
from typing import Protocol

from services.integrations.dto import (
    AnomalyDTO,
    AnomalySeverity,
    DataKind,
    NormalizedDataSetDTO,
    StatisticalSummaryDTO,
)


class MLModelPort(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def model_type(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def supported_data_kinds(self) -> list[DataKind]: ...

    @property
    def model_card(self) -> dict[str, object]: ...

    def supports(self, dataset: NormalizedDataSetDTO) -> bool: ...

    async def analyze(self, dataset: NormalizedDataSetDTO) -> dict[str, object]: ...


class DownsamplerPort(Protocol):
    @property
    def algorithm_name(self) -> str: ...

    def downsample(
        self,
        data: list[tuple[float, float]],
        target_points: int,
    ) -> list[tuple[float, float]]: ...
