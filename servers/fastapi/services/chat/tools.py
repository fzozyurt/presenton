import json
import logging
import re
from typing import Any, Awaitable, Callable

import dirtyjson  # type: ignore[import-untyped]
from llmai.shared import AssistantToolCall, Tool  # type: ignore[import-not-found]

from services.chat.schemas import (
    AnalyzeExternalDataInput,
    DeleteSlideInput,
    FetchExternalDataInput,
    GenerateAssetsInput,
    GenerateIconInput,
    GenerateImageInput,
    GetContentSchemaFromLayoutIdInput,
    GetSlideAtIndexInput,
    ListDataSourcesInput,
    ListMLModelsInput,
    NoArgsInput,
    RunMLModelInput,
    SaveSlideInput,
    SearchSlidesInput,
    SetPresentationThemeInput,
    SuggestChartInput,
    ValidateExternalDataInput,
)
from services.chat.presentation_context_store import PresentationContextStore

LOGGER = logging.getLogger(__name__)

ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class ChatTools:
    def __init__(self, memory: PresentationContextStore):
        self._memory = memory
        self._tool_handlers: dict[str, ToolHandler] = {
            "getPresentationOutline": self._get_presentation_outline,
            "searchSlides": self._search_slides,
            "getSlideAtIndex": self._get_slide_at_index,
            "getPresentationThemeCatalog": self._get_presentation_theme_catalog,
            "getAvailableLayouts": self._get_available_layouts,
            "getContentSchemaFromLayoutId": self._get_content_schema_from_layout_id,
            "generateAssets": self._generate_assets,
            "generateImage": self._generate_image,
            "generateIcon": self._generate_icon,
            "saveSlide": self._save_slide,
            "deleteSlide": self._delete_slide,
            "setPresentationTheme": self._set_presentation_theme,
            "fetchExternalData": self._fetch_external_data,
            "analyzeExternalData": self._analyze_external_data,
            "validateExternalData": self._validate_external_data,
            "runMLModel": self._run_ml_model,
            "suggestChart": self._suggest_chart,
            "listDataSources": self._list_data_sources,
            "listMLModels": self._list_ml_models,
        }

    def get_tool_definitions(self) -> list[Tool]:
        return [
            Tool(
                name="getPresentationOutline",
                description=(
                    "Live database: current deck structure. "
                    "Use for the **actual** slide list/order and compact previews—not for uploaded PDF text or pre-outline RAG. "
                    "Falls back to stored outlines only if no slide rows exist. "
                    "Return compact sections (no full slide JSON). Use for flow, sections, or 'what slides exist'."
                ),
                schema=NoArgsInput,
                strict=True,
            ),
            Tool(
                name="searchSlides",
                description=(
                    "Live SQL slides: keyword/semantic style search with snippets and indices. "
                    "Use to find on-slide text, topics, or which slide mentioned something. "
                    "For source-document-only questions, rely on deck memory; use this when the question is about **slides as built**. "
                    "Always provide both query and limit."
                ),
                schema=SearchSlidesInput,
                strict=True,
            ),
            Tool(
                name="getSlideAtIndex",
                description=(
                    "Live SQL: one slide by index—authoritative for exact current content. "
                    "Set includeFullContent=true when you need full JSON (before saveSlide or precise edits). "
                    "If user says slide N, use zero-based index N-1."
                ),
                schema=GetSlideAtIndexInput,
                strict=True,
            ),
            Tool(
                name="getPresentationThemeCatalog",
                description=(
                    "Read-only theme catalog for the current presentation. "
                    "Returns currently applied color theme and all available color themes "
                    "(built-in + saved custom themes). "
                    "Use this for questions like 'which theme is applied' or "
                    "'what themes are available'. "
                    "Do NOT use getAvailableLayouts for theme questions."
                ),
                schema=NoArgsInput,
                strict=True,
            ),
            Tool(
                name="getAvailableLayouts",
                description=(
                    "List slide layout ids/descriptions for the presentation template. "
                    "This is for content structure/layout selection only, not color themes."
                ),
                schema=NoArgsInput,
                strict=True,
            ),
            Tool(
                name="getContentSchemaFromLayoutId",
                description=(
                    "Fetch the JSON content schema for a layout id. Use before "
                    "saving slide content to validate structure."
                ),
                schema=GetContentSchemaFromLayoutIdInput,
                strict=True,
            ),
            Tool(
                name="generateAssets",
                description=(
                    "Generate multiple media assets in one call. Use for all slide "
                    "images and icons before saving content; include every needed "
                    "asset in the assets array instead of calling image/icon tools "
                    "one at a time."
                ),
                schema=GenerateAssetsInput,
                strict=True,
            ),
            Tool(
                name="saveSlide",
                description=(
                    "Save slide content for a layout. If replaceOldSlideAtIndex is "
                    "true, replace that index; otherwise insert as a new slide. "
                    "Pass content as a JSON-serialized object string and the server "
                    "will validate it against layout schema before save. "
                    "Returns saved:false with validation_errors when limits are exceeded—"
                    "typically shorten strings to satisfy maxLength, then call saveSlide again."
                ),
                schema=SaveSlideInput,
                strict=True,
            ),
            Tool(
                name="deleteSlide",
                description=(
                    "Delete an existing slide by zero-based index and reindex the "
                    "remaining slides. Use when the user asks to remove a slide."
                ),
                schema=DeleteSlideInput,
                strict=True,
            ),
            Tool(
                name="setPresentationTheme",
                description=(
                    "Change the deck theme using user-friendly requests like "
                    "'dark', 'light', theme name/id, or 'another'. "
                    "Can also apply customTheme payloads with colors/fonts and "
                    "optionally save them for reuse. Applies theme at presentation level. "
                    "Only use this when the user explicitly asks to change/apply/switch theme."
                ),
                schema=SetPresentationThemeInput,
                strict=True,
            ),
            Tool(
                name="fetchExternalData",
                description=(
                    "Query external data sources (Grafana dashboards, D databases, Prometheus, "
                    "custom HTTP APIs) to fetch metrics, time-series, or structured data. "
                    "Use this when the user asks for live data, dashboards, charts, "
                    "or any data from external monitoring/business systems. "
                    "The returned data is raw — you MUST analyze, summarize trends, "
                    "flag anomalies (threshold breaches), and format insights before "
                    "placing them into slide content. Always call this BEFORE saveSlide "
                    "when data is needed for the slide. "
                    "For Grafana: pass dashboard UID or panel description as query. "
                    "For D: pass SQL or qSQL. "
                    "For Prometheus: pass a PromQL query. "
                    "For custom_http/rest: pass the endpoint path."
                ),
                schema=FetchExternalDataInput,
                strict=True,
            ),
            Tool(
                name="analyzeExternalData",
                description=(
                    "Run deeper ML-powered statistical analysis on previously fetched external data. "
                    "Use after fetchExternalData to get Z-score anomalies, IQR outliers, trend detection, "
                    "and full statistical profiles. Focus options: 'trends', 'anomalies', 'distribution', "
                    "or omit for full analysis. Results include ML model findings ready for slide content."
                ),
                schema=AnalyzeExternalDataInput,
                strict=True,
            ),
            Tool(
                name="suggestChart",
                description=(
                    "Get chart type recommendations based on data characteristics. "
                    "Takes a DataKind value and optional constraint list of available chart types. "
                    "Returns the best chart type match with alternatives. Useful before choosing "
                    "a slide layout for data visualization."
                ),
                schema=SuggestChartInput,
                strict=True,
            ),
            Tool(
                name="listDataSources",
                description=(
                    "List all available external data sources registered in the integration layer. "
                    "Shows which adapters are active (grafana, rest, etc.) and their capabilities. "
                    "Use when the user asks what data sources are available."
                ),
                schema=ListDataSourcesInput,
                strict=True,
            ),
            Tool(
                name="validateExternalData",
                description=(
                    "Run ML-powered validation on previously fetched external data. "
                    "Use after fetchExternalData to get quality assessment: anomaly confidence "
                    "scores, distribution checks, trend validation. The output includes "
                    "a 'verdict' field (valid/suspect/inconclusive) and 'quality_issues' "
                    "array that helps you judge whether the data is reliable. "
                    "ALWAYS call this before putting external data into slides — "
                    "it helps catch bad/missing/anomalous data before presentation."
                ),
                schema=ValidateExternalDataInput,
                strict=True,
            ),
            Tool(
                name="runMLModel",
                description=(
                    "Run a specific ML model on previously fetched external data. "
                    "Use listMLModels first to see available models and their descriptions. "
                    "Each model specializes in one aspect: anomaly detection (zscore_anomaly, "
                    "iqr_anomaly), trend analysis (trend_detection), or baseline statistics "
                    "(statistical_baseline). Models return structured results you can use "
                    "directly in slide content."
                ),
                schema=RunMLModelInput,
                strict=True,
            ),
            Tool(
                name="listMLModels",
                description=(
                    "List all available ML models with their descriptions, capabilities, "
                    "and when to use each one. Use this to discover which models are best "
                    "for your current data before calling runMLModel or validateExternalData."
                ),
                schema=ListMLModelsInput,
                strict=True,
            ),
        ]

    async def execute_tool_call(self, tool_call: AssistantToolCall) -> dict[str, Any]:
        handler = self._tool_handlers.get(tool_call.name)
        if not handler:
            return {
                "ok": False,
                "tool": tool_call.name,
                "error": f"Unsupported tool: {tool_call.name}",
            }

        try:
            parsed_args = self._parse_args(tool_call.arguments)
            LOGGER.info("Executing chat tool %s", tool_call.name)
            result = await handler(parsed_args)
            return {"ok": True, "tool": tool_call.name, "result": result}
        except Exception as exc:
            LOGGER.exception("Chat tool failed: %s", tool_call.name)
            return {
                "ok": False,
                "tool": tool_call.name,
                "error": str(exc),
            }

    async def _get_presentation_outline(self, _: dict[str, Any]) -> dict[str, Any]:
        outline = await self._memory.get("presentation_outline")
        if not isinstance(outline, dict):
            return {
                "found": False,
                "message": "Presentation outline is not available in memory yet.",
                "sections": [],
            }

        slides = outline.get("slides")
        if not isinstance(slides, list) or not slides:
            return {
                "found": False,
                "message": "Presentation outline exists but has no slides.",
                "sections": [],
            }

        sections: list[dict[str, Any]] = []
        for position, slide in enumerate(slides):
            index = position
            content = ""
            if isinstance(slide, dict):
                raw_index = slide.get("index")
                if isinstance(raw_index, int):
                    index = raw_index
                raw_content = slide.get("content")
                if isinstance(raw_content, str):
                    content = raw_content
                elif raw_content is not None:
                    try:
                        content = json.dumps(raw_content, ensure_ascii=False)
                    except Exception:
                        content = str(raw_content)
            elif isinstance(slide, str):
                content = slide

            title = self._extract_title(content) or f"Slide {index + 1}"
            sections.append(
                {
                    "index": index,
                    "slide_number": index + 1,
                    "title": title,
                }
            )

        return {
            "found": True,
            "slide_count": len(sections),
            "sections": sections,
            "source": outline.get("source", "memory"),
        }

    async def _search_slides(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = SearchSlidesInput(**args)
        results = await self._memory.search(payload.query, payload.limit)
        return {
            "query": payload.query,
            "count": len(results),
            "results": results,
        }

    async def _get_slide_at_index(self, args: dict[str, Any]) -> dict[str, Any]:
        normalized_args = dict(args)
        normalized_args.setdefault("includeFullContent", False)
        payload = GetSlideAtIndexInput(**normalized_args)
        slide = await self._memory.get_slide_at_index(
            payload.index,
            include_full_content=payload.include_full_content,
        )
        if not slide and payload.index > 0:
            # Users often refer to slides as 1-based; allow a safe fallback.
            fallback_index = payload.index - 1
            fallback_slide = await self._memory.get_slide_at_index(
                fallback_index,
                include_full_content=payload.include_full_content,
            )
            if fallback_slide:
                return {
                    "found": True,
                    "slide": fallback_slide,
                    "requested_index": payload.index,
                    "resolved_index": fallback_index,
                    "note": (
                        "No slide found at requested index; returned one-based fallback "
                        f"at index {fallback_index}."
                    ),
                }
        if not slide:
            return {
                "found": False,
                "message": f"No slide found at index {payload.index}.",
            }
        return {
            "found": True,
            "slide": slide,
        }

    async def _get_available_layouts(self, _: dict[str, Any]) -> dict[str, Any]:
        layouts = await self._memory.get_available_layouts()
        return {
            "count": len(layouts),
            "layouts": layouts,
        }

    async def _get_presentation_theme_catalog(
        self, _: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._memory.get_presentation_theme_catalog()

    async def _get_content_schema_from_layout_id(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        payload = GetContentSchemaFromLayoutIdInput(**args)
        schema = await self._memory.get_content_schema_from_layout_id(payload.layout_id)
        if schema is None:
            return {
                "found": False,
                "layout_id": payload.layout_id,
                "message": "Layout schema not found for the provided layout id.",
            }
        return {
            "found": True,
            "layout_id": payload.layout_id,
            "content_schema": schema,
        }

    async def _generate_image(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = GenerateImageInput(**args)
        image_url = await self._memory.generate_image(payload.prompt)
        return {
            "prompt": payload.prompt,
            "url": image_url,
        }

    async def _generate_icon(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = GenerateIconInput(**args)
        icon_url = await self._memory.generate_icon(payload.query)
        return {
            "query": payload.query,
            "url": icon_url,
        }

    async def _generate_assets(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = GenerateAssetsInput(**args)
        generated_assets: list[dict[str, Any]] = []

        for index, asset in enumerate(payload.assets):
            if asset.kind == "image":
                result = await self._generate_image({"prompt": asset.prompt})
            else:
                result = await self._generate_icon({"query": asset.prompt})

            generated_assets.append(
                {
                    "index": index,
                    "kind": asset.kind,
                    "prompt": asset.prompt,
                    "url": result.get("url"),
                }
            )

        return {
            "count": len(generated_assets),
            "assets": generated_assets,
            "message": f"Generated {len(generated_assets)} asset(s).",
        }

    async def _save_slide(self, args: dict[str, Any]) -> dict[str, Any]:
        payload_args = json.loads(json.dumps(dict(args), ensure_ascii=False))
        raw_content = payload_args.get("content")
        if isinstance(raw_content, dict):
            payload_args["content"] = json.dumps(raw_content, ensure_ascii=False)

        payload = SaveSlideInput(**payload_args)
        try:
            content_parsed: Any = dirtyjson.loads(payload.content)
        except Exception:
            content_parsed = json.loads(payload.content)

        if not isinstance(content_parsed, dict):
            raise ValueError("'content' must be a JSON object.")

        content_payload = json.loads(json.dumps(content_parsed, ensure_ascii=False))
        return await self._memory.save_slide(
            content=content_payload,
            layout_id=payload.layout_id,
            index=payload.index,
            replace_old_slide_at_index=payload.replace_old_slide_at_index,
        )

    async def _delete_slide(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = DeleteSlideInput(**args)
        return await self._memory.delete_slide(index=payload.index)

    async def _set_presentation_theme(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = SetPresentationThemeInput(**args)
        return await self._memory.set_presentation_theme(
            theme_query=payload.theme,
            custom_theme=(
                payload.custom_theme.model_dump(exclude_none=True)
                if payload.custom_theme is not None
                else None
            ),
            save_custom_theme=bool(payload.save_custom_theme),
        )

    async def _fetch_external_data(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = FetchExternalDataInput(**args)
        return await self._memory.fetch_external_data(
            source=payload.source,
            query=payload.query,
            limit=payload.limit or 50,
        )

    async def _analyze_external_data(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = AnalyzeExternalDataInput(**args)
        return await self._memory.analyze_external_data(
            source=payload.source,
            query=payload.query,
            focus=payload.focus,
        )

    async def _suggest_chart(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = SuggestChartInput(**args)
        return self._suggest_chart_type(
            data_kind=payload.data_kind,
            description=payload.description,
            available_chart_types=payload.available_chart_types,
        )

    async def _list_data_sources(self, _: dict[str, Any]) -> dict[str, Any]:
        return self._list_available_data_sources()

    async def _validate_external_data(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = ValidateExternalDataInput(**args)
        return await self._memory.validate_external_data(
            source=payload.source,
            query=payload.query,
            model_names=payload.model_names,
            focus=payload.focus,
        )

    async def _run_ml_model(self, args: dict[str, Any]) -> dict[str, Any]:
        payload = RunMLModelInput(**args)
        return await self._memory.run_ml_model(
            source=payload.source,
            query=payload.query,
            model_name=payload.model_name,
        )

    async def _list_ml_models(self, _: dict[str, Any]) -> dict[str, Any]:
        return self._list_ml_models_catalog()

    @staticmethod
    def _parse_args(arguments: str | None) -> dict[str, Any]:
        if not arguments:
            return {}

        try:
            parsed = dirtyjson.loads(arguments)
        except Exception:
            parsed = json.loads(arguments)

        normalized = json.loads(json.dumps(parsed, ensure_ascii=False))
        if isinstance(normalized, dict):
            return normalized

        raise ValueError("Tool arguments must be a JSON object.")

    @staticmethod
    def _extract_title(markdown_content: str) -> str:
        for line in markdown_content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading_match = re.match(r"^#{1,6}\s*(.+?)\s*$", stripped)
            if heading_match:
                return heading_match.group(1).strip()
            return stripped[:120]
        return ""

    @staticmethod
    def _suggest_chart_type(
        data_kind: str,
        description: str | None = None,
        available_chart_types: list[str] | None = None,
    ) -> dict[str, Any]:
        kind_chart_map: dict[str, list[str]] = {
            "time_series": ["line", "area", "column"],
            "categorical": ["bar", "column", "pie", "donut"],
            "single_value": ["scorecard", "gauge"],
            "multi_value": ["bar", "column", "radar"],
            "matrix": ["heatmap"],
            "table": ["table"],
            "histogram": ["histogram", "bar"],
            "text": ["none"],
        }
        primary = kind_chart_map.get(data_kind, ["table"])[0]
        alternatives = kind_chart_map.get(data_kind, ["table"])[1:]
        if available_chart_types:
            available_lower = {c.lower() for c in available_chart_types}
            alternatives = [a for a in alternatives if a in available_lower]
            if primary not in available_lower and alternatives:
                primary = alternatives[0]
                alternatives = alternatives[1:]
        return {
            "data_kind": data_kind,
            "primary_chart": primary,
            "alternatives": alternatives,
            "reason": f"Best chart for {data_kind} data based on data shape.",
            "description": description,
        }

    @staticmethod
    def _list_available_data_sources() -> dict[str, Any]:
        try:
            from services.integrations.registry import get_adapter_registry
            from services.integrations.adapter_schema import AdapterSchemaProvider

            registry = get_adapter_registry()
            if not registry.list_types():
                from services.chat.memory_layer import _init_adapters
                _init_adapters(registry)
            types = registry.list_types()

            schemas = {}
            for t in types:
                s = AdapterSchemaProvider.get_schema(t)
                if s:
                    schemas[t] = {
                        "description": s.get("description"),
                        "required": s.get("required_config"),
                        "optional": s.get("optional_config"),
                        "supports": s.get("supports"),
                        "fixture_mode": s.get("fixture_mode"),
                    }

            return {
                "available": True,
                "adapter_types": types,
                "count": len(types),
                "schemas": schemas,
                "note": "Use fetchExternalData with any of these source types. See schema for required config per adapter.",
            }
        except Exception:
            return {
                "available": True,
                "adapter_types": ["grafana", "rest", "d_database", "prometheus", "custom_http"],
                "count": 5,
                "note": "Fallback listing. Real adapter registry may have additional types.",
            }

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[:limit]}..."

    @staticmethod
    def _list_ml_models_catalog() -> dict[str, Any]:
        try:
            from services.integrations.ml.registry import get_ml_registry
            registry = get_ml_registry()
            catalog = registry.get_agent_catalog()
            return {
                "available": True,
                "models": catalog,
                "count": len(catalog),
                "usage_guide": (
                    "Each model has a 'when_to_use' field explaining the right scenario. "
                    "Use runMLModel with the model_name to execute. "
                    "For comprehensive validation, use validateExternalData which runs all compatible models."
                ),
            }
        except Exception:
            return {"available": False, "models": [], "error": "ML registry not available."}
