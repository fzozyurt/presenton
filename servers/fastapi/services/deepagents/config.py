from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast


MemoryMode = Literal["off", "review", "auto"]
OrchestratorMode = Literal["legacy", "deepagents"]

_SUPPORTED_ORCHESTRATORS: set[str] = {"legacy", "deepagents"}
_SUPPORTED_MEMORY_MODES: set[str] = {"off", "review", "auto"}


@dataclass
class DeepAgentsSettings:
    presentation_orchestrator: str = "legacy"
    deepagents_enabled: bool = False
    deepagents_model_provider: str = "openai"
    deepagents_model_name: str = "gpt-4.1-mini"
    deepagents_memory_mode: str = "review"
    deepagents_auto_mode: bool = False
    deepagents_mcp_url: str = "http://127.0.0.1:8001/mcp"
    deepagents_max_retries: int = 2
    deepagents_max_qa_loops: int = 1
    deepagents_run_timeout_seconds: int = 900

    @property
    def deepagents_model(self) -> str:
        return f"{self.deepagents_model_provider}:{self.deepagents_model_name}"

    @property
    def is_deepagents_mode(self) -> bool:
        return self.presentation_orchestrator == "deepagents" or self.deepagents_enabled

    @property
    def orchestrator_mode(self) -> OrchestratorMode:
        if self.presentation_orchestrator not in _SUPPORTED_ORCHESTRATORS:
            return cast("OrchestratorMode", "legacy")
        return cast("OrchestratorMode", self.presentation_orchestrator)

    @property
    def memory_mode(self) -> MemoryMode:
        if self.deepagents_memory_mode not in _SUPPORTED_MEMORY_MODES:
            return cast("MemoryMode", "review")
        return cast("MemoryMode", self.deepagents_memory_mode)


def load_deepagents_settings() -> DeepAgentsSettings:
    from utils.get_env import (
        get_deepagents_auto_mode_env,
        get_deepagents_enabled_env,
        get_deepagents_max_qa_loops_env,
        get_deepagents_max_retries_env,
        get_deepagents_mcp_url_env,
        get_deepagents_memory_mode_env,
        get_deepagents_model_name_env,
        get_deepagents_model_provider_env,
        get_deepagents_run_timeout_seconds_env,
        get_presentation_orchestrator_env,
        is_deepagents_auto_mode,
        is_deepagents_enabled,
    )

    return DeepAgentsSettings(
        presentation_orchestrator=get_presentation_orchestrator_env(),
        deepagents_enabled=is_deepagents_enabled(),
        deepagents_model_provider=get_deepagents_model_provider_env(),
        deepagents_model_name=get_deepagents_model_name_env(),
        deepagents_memory_mode=get_deepagents_memory_mode_env(),
        deepagents_auto_mode=is_deepagents_auto_mode(),
        deepagents_mcp_url=get_deepagents_mcp_url_env(),
        deepagents_max_retries=int(get_deepagents_max_retries_env()),
        deepagents_max_qa_loops=int(get_deepagents_max_qa_loops_env()),
        deepagents_run_timeout_seconds=int(get_deepagents_run_timeout_seconds_env()),
    )
