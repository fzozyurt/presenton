from __future__ import annotations

import logging

from services.integrations.ml.ports import MLModelPort
from services.integrations.dto import DataKind, NormalizedDataSetDTO

LOGGER = logging.getLogger(__name__)


class StaticMLModelRegistry:
    def __init__(self, models: list[MLModelPort] | None = None):
        self._models: dict[str, MLModelPort] = {}
        if models:
            for model in models:
                self.register(model)

    def register(self, model: MLModelPort) -> None:
        key = model.model_name.lower()
        self._models[key] = model
        LOGGER.info("Registered ML model: %s (%s)", model.model_name, model.model_type)

    def get(self, model_name: str) -> MLModelPort:
        key = model_name.lower()
        if key not in self._models:
            available = list(self._models.keys())
            raise KeyError(f"No ML model registered: {model_name!r}. Available: {available}")
        return self._models[key]

    def select_supported(
        self,
        dataset: NormalizedDataSetDTO,
        model_types: list[str] | None = None,
        model_names: list[str] | None = None,
    ) -> list[MLModelPort]:
        selected: list[MLModelPort] = []
        for model in self._models.values():
            if model_names and model.model_name not in model_names:
                continue
            if model_types and model.model_type not in model_types:
                continue
            if model.supports(dataset):
                selected.append(model)
        return selected

    def smart_select(
        self,
        dataset: NormalizedDataSetDTO,
        *,
        focus: str | None = None,
        max_models: int = 5,
    ) -> list[MLModelPort]:
        """Intelligently select ML models based on data characteristics and focus.

        Priority:
        1. Always include baseline for context
        2. If focus='anomalies': Z-score + IQR (both for coverage)
        3. If focus='trends' and TIME_SERIES: trend_detection + seasonal_decomposition
        4. If focus='changes': change_point_detection
        5. If focus='compare': distribution_comparison
        6. Fall back to all compatible models
        """
        selected: list[MLModelPort] = []

        if not focus:
            return self.select_supported(dataset)[:max_models]

        focus = focus.lower()

        baseline = self._models.get("statistical_baseline")
        if baseline and baseline.supports(dataset):
            selected.append(baseline)

        if "anomal" in focus:
            for name in ("zscore_anomaly", "iqr_anomaly"):
                m = self._models.get(name)
                if m and m.supports(dataset) and m not in selected:
                    selected.append(m)

        if "trend" in focus or "season" in focus or "decompos" in focus:
            for name in ("trend_detection", "seasonal_decomposition"):
                m = self._models.get(name)
                if m and m.supports(dataset) and m not in selected:
                    selected.append(m)

        if "change" in focus or "shift" in focus or "deploy" in focus:
            for name in ("change_point_detection",):
                m = self._models.get(name)
                if m and m.supports(dataset) and m not in selected:
                    selected.append(m)

        if "compar" in focus or "distrib" in focus or "wow" in focus:
            for name in ("distribution_comparison",):
                m = self._models.get(name)
                if m and m.supports(dataset) and m not in selected:
                    selected.append(m)

        if len(selected) < 2:
            remaining = [
                m for m in self._models.values()
                if m.supports(dataset) and m not in selected
            ]
            selected.extend(remaining[: max_models - len(selected)])

        return selected[:max_models]

    def list_models(self) -> list[str]:
        return list(self._models.keys())

    def get_agent_catalog(self) -> list[dict[str, object]]:
        """Return model descriptions formatted for LLM Agent consumption."""
        catalog: list[dict[str, object]] = []
        for model in self._models.values():
            catalog.append({
                "model_name": model.model_name,
                "model_type": model.model_type,
                "description": model.description,
                "supported_data_kinds": [k.value for k in model.supported_data_kinds],
                "card": model.model_card,
            })
        return catalog


_registry: StaticMLModelRegistry | None = None


def get_ml_registry() -> StaticMLModelRegistry:
    global _registry
    if _registry is None:
        _registry = StaticMLModelRegistry()
        _init_default_models(_registry)
    return _registry


def _init_default_models(registry: StaticMLModelRegistry) -> None:
    from services.integrations.ml.models import (
        StatisticalBaselineModel,
        ZScoreAnomalyModel,
        TrendDetectionModel,
        IQRAnomalyModel,
        ChangePointDetectionModel,
        SeasonalDecompositionModel,
        DistributionComparisonModel,
    )
    registry.register(StatisticalBaselineModel())
    registry.register(ZScoreAnomalyModel())
    registry.register(TrendDetectionModel())
    registry.register(IQRAnomalyModel())
    registry.register(ChangePointDetectionModel())
    registry.register(SeasonalDecompositionModel())
    registry.register(DistributionComparisonModel())

__all__ = ["StaticMLModelRegistry", "get_ml_registry"]
