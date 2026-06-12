from __future__ import annotations

import pytest

from services.deepagents.errors import PermissionDeniedError
from services.deepagents.permissions import (
    DeepAgentsPermissionPolicy,
    PathPermissionRule,
    _build_filesystem_permission_rules,
)


class TestPathPermissionRule:
    def test_matches_prefix(self) -> None:
        rule = PathPermissionRule("/inputs/", allow_read=True, allow_write=False)
        assert rule.matches("/inputs/a.txt") is True
        assert rule.matches("/inputs/") is True
        assert rule.matches("/workspace/b.txt") is False

    def test_allow_write_access(self) -> None:
        rule = PathPermissionRule("/workspace/", allow_read=True, allow_write=True)
        assert rule.allow_write is True


class TestDeepAgentsPermissionPolicy:
    def test_inputs_write_denied(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="off")
        assert policy.can_write("/inputs/a.txt") is False

    def test_workspace_write_allowed(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="off")
        assert policy.can_write("/workspace/a.txt") is True

    def test_outputs_write_allowed(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="off")
        assert policy.can_write("/outputs/a.json") is True

    def test_memories_write_denied_in_off(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="off")
        assert policy.can_write("/memories/a.md") is False

    def test_memories_write_denied_in_review(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="review")
        assert policy.can_write("/memories/a.md") is False

    def test_memories_write_allowed_in_auto(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="auto")
        assert policy.can_write("/memories/a.md") is True

    def test_check_write_permission_raises(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="off")
        with pytest.raises(PermissionDeniedError):
            policy.check_write_permission("/inputs/secret.txt")

    def test_check_write_permission_passes(self) -> None:
        policy = DeepAgentsPermissionPolicy(memory_mode="auto")
        policy.check_write_permission("/workspace/data.txt")


def test_build_filesystem_permission_rules_structure() -> None:
    rules = _build_filesystem_permission_rules("off")
    assert isinstance(rules, list)
    all_rule_paths = sum((r["paths"] for r in rules), start=[])
    assert "/workspace/**" in all_rule_paths
    assert "/outputs/**" in all_rule_paths
    assert "/inputs/**" in all_rule_paths
