class DeepAgentsError(Exception):
    """Base exception for Deep Agents orchestration layer."""


class MCPUnavailableError(DeepAgentsError):
    """Raised when the MCP server is unreachable or returns no tools."""


class AgentFactoryError(DeepAgentsError):
    """Raised when agent construction fails."""


class PermissionDeniedError(DeepAgentsError):
    """Raised when a filesystem write is denied by the permission policy."""


class MemoryModeError(DeepAgentsError):
    """Raised when a memory operation is not allowed by the current mode."""


class RunTimeoutError(DeepAgentsError):
    """Raised when a Deep Agent run exceeds the configured timeout."""


class RunStateError(DeepAgentsError):
    """Raised when the job run state is invalid or inconsistent."""
