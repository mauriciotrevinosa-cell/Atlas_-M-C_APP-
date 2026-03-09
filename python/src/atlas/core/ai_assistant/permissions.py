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

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Dict, List, Optional


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

    def get_permissions(self, agent_name: str) -> Optional[AgentPermissions]:
        return self._perms.get(agent_name)

    def level_for(self, agent_name: str) -> PermissionLevel:
        perm = self._perms.get(agent_name)
        return perm.level if perm else PermissionLevel.READ_ONLY

    def allowed_tools_for(self, agent_name: str) -> List[str]:
        perm = self._perms.get(agent_name)
        return perm.allowed_tools if perm else []

    def __repr__(self) -> str:
        return f"PermissionChecker(agents={list(self._perms.keys())})"


# ── Module-level singleton ────────────────────────────────────────────────────
_checker: Optional[PermissionChecker] = None


def get_checker() -> PermissionChecker:
    global _checker
    if _checker is None:
        _checker = PermissionChecker()
    return _checker
