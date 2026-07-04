"""
Agent Permission System — controls what each agent is allowed to do.

Principle: agents have the minimum permissions needed for their task.
No agent can autonomously merge, delete, deploy, or modify production.

Permission levels (ascending):
  READ_ONLY   → can read files, context, logs
  PROPOSE     → can generate plans, code proposals, reviews
  WRITE_DRAFT → can write to draft/staging areas
  EXECUTE     → can run tests, linters, safe scripts
  ADMIN       → reserved for human operators only

Each agent has a static permission level.
The orchestrator checks permissions before dispatching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Iterable, List, Optional

from atlas.core.ai_assistant.task_schema import AgentTask


class PermissionLevel(IntEnum):
    READ_ONLY   = 1
    PROPOSE     = 2
    WRITE_DRAFT = 3
    EXECUTE     = 4
    ADMIN       = 99   # humans only


@dataclass
class AgentPermissions:
    """Permission spec for one agent."""
    agent_name:       str
    level:            PermissionLevel
    allowed_tools:    List[str]      # explicit tool whitelist
    blocked_tools:    List[str]      # explicit blacklist (overrides allowed)
    can_write_files:  bool = False
    can_run_scripts:  bool = False
    can_call_apis:    bool = False   # external API calls

    def can_use_tool(self, tool: str) -> bool:
        if tool in self.blocked_tools:
            return False
        if not self.allowed_tools:
            return True  # no whitelist = all tools allowed for this level
        return tool in self.allowed_tools

    def has_level(self, required: PermissionLevel) -> bool:
        return self.level >= required


# ── Static permission table ────────────────────────────────────────────────────
# Default permissions per agent. Override via config if needed.

AGENT_PERMISSIONS: Dict[str, AgentPermissions] = {

    "planner_agent": AgentPermissions(
        agent_name    = "planner_agent",
        level         = PermissionLevel.PROPOSE,
        allowed_tools = ["read_file", "summarize_context", "list_files"],
        blocked_tools = ["write_file", "run_script", "git_commit", "deploy"],
        can_write_files = False,
        can_run_scripts = False,
        can_call_apis   = False,
    ),

    "reviewer_agent": AgentPermissions(
        agent_name    = "reviewer_agent",
        level         = PermissionLevel.PROPOSE,
        allowed_tools = ["read_file", "read_diff", "run_linter"],
        blocked_tools = ["write_file", "git_commit", "deploy", "merge"],
        can_write_files = False,
        can_run_scripts = False,
        can_call_apis   = False,
    ),

    "test_agent": AgentPermissions(
        agent_name    = "test_agent",
        level         = PermissionLevel.WRITE_DRAFT,
        allowed_tools = ["read_file", "write_test_file", "run_pytest"],
        blocked_tools = ["git_commit", "deploy", "merge", "delete_file"],
        can_write_files = True,   # can write test files to draft area
        can_run_scripts = True,   # can run pytest
        can_call_apis   = False,
    ),

    "context_curator_agent": AgentPermissions(
        agent_name    = "context_curator_agent",
        level         = PermissionLevel.READ_ONLY,
        allowed_tools = ["read_file", "read_memory", "summarize_context"],
        blocked_tools = ["write_file", "run_script", "git_commit", "deploy"],
        can_write_files = False,
        can_run_scripts = False,
        can_call_apis   = False,
    ),

    "code_builder_agent": AgentPermissions(
        agent_name    = "code_builder_agent",
        level         = PermissionLevel.WRITE_DRAFT,
        allowed_tools = ["read_file", "write_draft_file", "read_diff"],
        blocked_tools = ["git_commit", "deploy", "merge", "run_script"],
        can_write_files = True,   # draft files only
        can_run_scripts = False,
        can_call_apis   = False,
    ),

    "repo_scout_agent": AgentPermissions(
        agent_name    = "repo_scout_agent",
        level         = PermissionLevel.READ_ONLY,
        allowed_tools = ["web_search", "read_url", "summarize_content"],
        blocked_tools = ["write_file", "run_script", "git_commit", "deploy", "download"],
        can_write_files = False,
        can_run_scripts = False,
        can_call_apis   = True,   # can do web searches
    ),

    "ingestion_agent": AgentPermissions(
        agent_name    = "ingestion_agent",
        level         = PermissionLevel.WRITE_DRAFT,
        allowed_tools = ["read_file", "read_url", "write_knowledge_pack"],
        blocked_tools = ["git_commit", "deploy", "merge", "run_script"],
        can_write_files = True,   # knowledge pack files only
        can_run_scripts = False,
        can_call_apis   = True,
    ),

    "docs_agent": AgentPermissions(
        agent_name    = "docs_agent",
        level         = PermissionLevel.PROPOSE,
        allowed_tools = ["read_file", "summarize_context", "write_draft_doc"],
        blocked_tools = ["git_commit", "deploy", "merge", "run_script"],
        can_write_files = True,
        can_run_scripts = False,
        can_call_apis   = False,
    ),

    "market_intel_agent": AgentPermissions(
        agent_name    = "market_intel_agent",
        level         = PermissionLevel.READ_ONLY,
        allowed_tools = [
            "read_market_events",
            "read_signal_terminal",
            "read_provider_health",
            "summarize_context",
        ],
        blocked_tools = ["write_file", "run_script", "git_commit", "deploy", "place_order"],
        can_write_files = False,
        can_run_scripts = False,
        can_call_apis   = False,
    ),
}


# ── Blocked actions for ALL agents (absolute limits) ──────────────────────────
GLOBALLY_BLOCKED = {
    "git_merge",
    "git_push_force",
    "deploy_production",
    "delete_database",
    "modify_schema_production",
    "empty_trash",
    "grant_admin_access",
    "modify_security_rules",
}


# ── Permission checker ────────────────────────────────────────────────────────

@dataclass
class PreflightDecision:
    """Agent gateway preflight result."""

    allowed: bool
    reason: str
    agent_name: str
    risk_level: str
    requested_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    mode: str = "paper"
    requires_approval: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "agent_name": self.agent_name,
            "risk_level": self.risk_level,
            "requested_tools": self.requested_tools,
            "denied_tools": self.denied_tools,
            "mode": self.mode,
            "requires_approval": self.requires_approval,
        }


class PermissionChecker:
    """Checks agent permissions before task execution."""

    def __init__(self, permissions: Optional[Dict[str, AgentPermissions]] = None):
        self._perms = permissions or AGENT_PERMISSIONS

    def check(self, agent_name: str, tool: str = "", action: str = "") -> tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str).

        Checks in order:
          1. Global block list
          2. Agent permission table
          3. Tool whitelist/blacklist
        """
        target = tool or action

        # 1. Global block
        if target in GLOBALLY_BLOCKED:
            return False, f"'{target}' is globally blocked for all agents"

        # 2. Agent permissions
        perm = self._perms.get(agent_name)
        if perm is None:
            return True, "no permission rule defined (permissive default)"

        # 3. Tool check
        if target and not perm.can_use_tool(target):
            return False, f"Agent '{agent_name}' is not allowed to use '{target}'"

        return True, "allowed"

    def preflight(self, task: AgentTask) -> PreflightDecision:
        """
        Deny unsafe agent tasks before dispatch.

        This is intentionally conservative: production/live trading and global
        destructive actions are blocked at the gateway even if an agent prompt
        requests them.
        """
        requested_tools = self.requested_tools(task)
        denied_tools: List[str] = []

        mode = self._task_mode(task)
        if mode in {"live", "production", "real", "real_money"}:
            return PreflightDecision(
                allowed=False,
                reason="live or production execution is blocked for agents; use paper/sandbox mode",
                agent_name=task.agent_name,
                risk_level=task.risk_level,
                requested_tools=requested_tools,
                mode=mode,
            )

        if task.risk_level == "critical" and not self._human_approved(task):
            return PreflightDecision(
                allowed=False,
                reason="critical-risk tasks require explicit human approval",
                agent_name=task.agent_name,
                risk_level=task.risk_level,
                requested_tools=requested_tools,
                mode=mode,
                requires_approval=True,
            )

        for tool in requested_tools:
            allowed, _ = self.check(task.agent_name, tool=tool)
            if not allowed:
                denied_tools.append(tool)

        if denied_tools:
            return PreflightDecision(
                allowed=False,
                reason="one or more requested tools are denied by agent permissions",
                agent_name=task.agent_name,
                risk_level=task.risk_level,
                requested_tools=requested_tools,
                denied_tools=denied_tools,
                mode=mode,
            )

        return PreflightDecision(
            allowed=True,
            reason="allowed",
            agent_name=task.agent_name,
            risk_level=task.risk_level,
            requested_tools=requested_tools,
            mode=mode,
        )

    def requested_tools(self, task: AgentTask) -> List[str]:
        """Collect tool/action requests from the task envelope."""
        tools: List[str] = []
        tools.extend(str(tool) for tool in task.allowed_tools if str(tool).strip())

        for payload in (task.context, task.inputs):
            for key in ("requested_tools", "tools", "tool_calls", "actions"):
                tools.extend(self._coerce_tool_names(payload.get(key)))

        seen = set()
        unique: List[str] = []
        for tool in tools:
            normalized = tool.strip()
            if normalized and normalized not in seen:
                unique.append(normalized)
                seen.add(normalized)
        return unique

    def get_permissions(self, agent_name: str) -> Optional[AgentPermissions]:
        return self._perms.get(agent_name)

    def level_for(self, agent_name: str) -> PermissionLevel:
        perm = self._perms.get(agent_name)
        return perm.level if perm else PermissionLevel.READ_ONLY

    def allowed_tools_for(self, agent_name: str) -> List[str]:
        perm = self._perms.get(agent_name)
        return perm.allowed_tools if perm else []

    @staticmethod
    def _coerce_tool_names(value: Any) -> Iterable[str]:
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            name = value.get("name") or value.get("tool") or value.get("action")
            return [str(name)] if name else []
        if isinstance(value, (list, tuple, set)):
            names: List[str] = []
            for item in value:
                names.extend(PermissionChecker._coerce_tool_names(item))
            return names
        return []

    @staticmethod
    def _task_mode(task: AgentTask) -> str:
        for payload in (task.context, task.inputs):
            for key in ("mode", "trading_mode", "execution_mode", "environment"):
                value = payload.get(key)
                if value:
                    return str(value).strip().lower()
        return "paper"

    @staticmethod
    def _human_approved(task: AgentTask) -> bool:
        return bool(
            task.context.get("human_approved")
            or task.context.get("approved_by_human")
            or task.inputs.get("human_approved")
            or task.inputs.get("approved_by_human")
        )

    def __repr__(self) -> str:
        return f"PermissionChecker(agents={list(self._perms.keys())})"


# ── Module-level singleton ────────────────────────────────────────────────────
_checker: Optional[PermissionChecker] = None


def get_checker() -> PermissionChecker:
    global _checker
    if _checker is None:
        _checker = PermissionChecker()
    return _checker
