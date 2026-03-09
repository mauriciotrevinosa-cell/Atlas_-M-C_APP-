"""
Permissions System — Controls what the AI can see, use, and execute.

Levels:
  - ADMIN: Full access (default for Atlas desktop app)
  - USER: Standard access (no code execution, no file writes)
  - READONLY: Read-only (can query data, no actions)
  - GUEST: Minimal (conversation only)

Usage:
    perms = Permissions(role="admin")
    if perms.can("execute_code"):
        # proceed
    perms.check("write_file")  # raises PermissionError if denied
"""

from typing import Set, Dict, Optional
from dataclasses import dataclass


@dataclass
class PermissionSet:
    """Named set of permissions."""
    name: str
    allowed_tools: Set[str]
    allowed_categories: Set[str]
    can_execute_code: bool
    can_write_files: bool
    can_access_financials: bool
    can_modify_settings: bool
    can_use_web: bool
    max_tokens: int


# Pre-defined permission sets
PERMISSION_SETS: Dict[str, PermissionSet] = {
    "admin": PermissionSet(
        name="admin",
        allowed_tools={"get_data", "web_search", "execute_code", "create_file",
                       "read_file", "image_gen"},
        allowed_categories={"project_data", "financial_analysis", "market_data",
                           "code_execution", "web_search", "document_query",
                           "conversation"},
        can_execute_code=True,
        can_write_files=True,
        can_access_financials=True,
        can_modify_settings=True,
        can_use_web=True,
        max_tokens=8192,
    ),
    "user": PermissionSet(
        name="user",
        allowed_tools={"get_data", "web_search", "read_file"},
        allowed_categories={"project_data", "financial_analysis", "market_data",
                           "web_search", "document_query", "conversation"},
        can_execute_code=False,
        can_write_files=False,
        can_access_financials=True,
        can_modify_settings=False,
        can_use_web=True,
        max_tokens=4096,
    ),
    "readonly": PermissionSet(
        name="readonly",
        allowed_tools={"get_data", "read_file"},
        allowed_categories={"project_data", "document_query", "conversation"},
        can_execute_code=False,
        can_write_files=False,
        can_access_financials=True,
        can_modify_settings=False,
        can_use_web=False,
        max_tokens=2048,
    ),
    "guest": PermissionSet(
        name="guest",
        allowed_tools=set(),
        allowed_categories={"conversation"},
        can_execute_code=False,
        can_write_files=False,
        can_access_financials=False,
        can_modify_settings=False,
        can_use_web=False,
        max_tokens=1024,
    ),
}


class Permissions:
    """
    Permission checker for AI operations.
    """

    def __init__(self, role: str = "admin"):
        if role not in PERMISSION_SETS:
            raise ValueError(
                f"Unknown role '{role}'. Available: {list(PERMISSION_SETS.keys())}"
            )
        self.role = role
        self._perms = PERMISSION_SETS[role]
        self._denied_log = []

    def can(self, action: str) -> bool:
        """Check if an action is permitted."""
        # Tool check
        if action in {"get_data", "web_search", "execute_code", "create_file",
                       "read_file", "image_gen"}:
            return action in self._perms.allowed_tools

        # Category check
        if action in {"project_data", "financial_analysis", "market_data",
                      "code_execution", "web_search", "document_query",
                      "conversation"}:
            return action in self._perms.allowed_categories

        # Specific capability checks
        checks = {
            "execute_code": self._perms.can_execute_code,
            "write_files": self._perms.can_write_files,
            "access_financials": self._perms.can_access_financials,
            "modify_settings": self._perms.can_modify_settings,
            "use_web": self._perms.can_use_web,
        }

        return checks.get(action, False)

    def check(self, action: str):
        """
        Check permission and raise if denied.

        Args:
            action: Action to check

        Raises:
            PermissionError: If action is not allowed
        """
        if not self.can(action):
            self._denied_log.append(action)
            raise PermissionError(
                f"Permission denied: '{action}' is not allowed for role '{self.role}'. "
                f"Required role: admin or user with specific permissions."
            )

    def get_allowed_tools(self) -> Set[str]:
        """Get set of tools this role can use."""
        return self._perms.allowed_tools

    def get_max_tokens(self) -> int:
        """Get max tokens for this role."""
        return self._perms.max_tokens

    def get_denied_log(self) -> list:
        """Get log of denied permission attempts."""
        return self._denied_log

    def get_info(self) -> Dict:
        """Get permission set info."""
        return {
            "role": self.role,
            "allowed_tools": list(self._perms.allowed_tools),
            "allowed_categories": list(self._perms.allowed_categories),
            "can_execute_code": self._perms.can_execute_code,
            "can_write_files": self._perms.can_write_files,
            "can_access_financials": self._perms.can_access_financials,
            "denied_attempts": len(self._denied_log),
        }
