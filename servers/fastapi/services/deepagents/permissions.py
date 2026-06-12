from __future__ import annotations

from typing import Any


class PathPermissionRule:
    def __init__(
        self,
        path_prefix: str,
        allow_read: bool = True,
        allow_write: bool = False,
    ) -> None:
        self.path_prefix = path_prefix
        self.allow_read = allow_read
        self.allow_write = allow_write

    def matches(self, path: str) -> bool:
        return path.startswith(self.path_prefix)


class DeepAgentsPermissionPolicy:
    def __init__(self, memory_mode: str) -> None:
        self.memory_mode = memory_mode
        self._rules = self._build_rules()

    def _build_rules(self) -> list[PathPermissionRule]:
        rules = [
            PathPermissionRule("/inputs/", allow_read=True, allow_write=False),
            PathPermissionRule("/workspace/", allow_read=True, allow_write=True),
            PathPermissionRule("/outputs/", allow_read=True, allow_write=True),
            PathPermissionRule("/config/", allow_read=True, allow_write=False),
        ]
        if self.memory_mode == "auto":
            rules.append(
                PathPermissionRule("/memories/", allow_read=True, allow_write=True)
            )
        elif self.memory_mode == "review":
            rules.append(
                PathPermissionRule("/memories/", allow_read=True, allow_write=False)
            )
        else:
            rules.append(
                PathPermissionRule("/memories/", allow_read=False, allow_write=False)
            )

        return rules

    def can_read(self, path: str) -> bool:
        for rule in self._rules:
            if rule.matches(path):
                return rule.allow_read
        return True

    def can_write(self, path: str) -> bool:
        normalized = path.replace("\\", "/")

        unsafe_prefixes = ["/secrets/", "/.env"]
        for prefix in unsafe_prefixes:
            if normalized.startswith(prefix):
                return False

        for rule in self._rules:
            if rule.matches(normalized):
                return rule.allow_write
        return False

    def check_write_permission(self, path: str) -> None:
        from .errors import PermissionDeniedError

        if not self.can_write(path):
            raise PermissionDeniedError(f"Write denied for path: {path}")


def _build_filesystem_permission_rules(memory_mode: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = [
        {"operations": ["read", "write"], "paths": ["/workspace/**"], "mode": "allow"},
        {"operations": ["read", "write"], "paths": ["/outputs/**"], "mode": "allow"},
        {"operations": ["read"], "paths": ["/inputs/**"], "mode": "allow"},
        {
            "operations": ["write"],
            "paths": ["/inputs/**", "/secrets/**", "/.env*", "/config/**"],
            "mode": "deny",
        },
    ]

    if memory_mode == "auto":
        rules.append(
            {
                "operations": ["read", "write"],
                "paths": ["/memories/**"],
                "mode": "allow",
            }
        )
    elif memory_mode == "review":
        rules.append(
            {"operations": ["read"], "paths": ["/memories/**"], "mode": "allow"}
        )
        rules.append(
            {"operations": ["write"], "paths": ["/memories/**"], "mode": "deny"}
        )
    else:
        rules.append(
            {"operations": ["read", "write"], "paths": ["/memories/**"], "mode": "deny"}
        )

    return rules


def build_filesystem_permissions(memory_mode: str) -> list[Any]:
    """
    Build a list of FilesystemPermission objects compatible with
    create_deep_agent(..., permissions=...).

    memory_mode values:
    - off: no memory access
    - review: memory read-only, writes go to /outputs/
    - auto: full memory access (still blocks secrets/source code)
    """
    from deepagents.middleware.filesystem import FilesystemPermission

    raw_rules = _build_filesystem_permission_rules(memory_mode)
    return [
        FilesystemPermission(
            operations=r["operations"],
            paths=r["paths"],
            mode=r["mode"],
        )
        for r in raw_rules
    ]
