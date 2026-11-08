"""Deprecated shim — import from furniture_cad.tools.oracle_set instead.

Kept so older tests and CLI flags (--freeze-set) keep working during R0.
"""

from __future__ import annotations

from furniture_cad.tools.oracle_set import (  # noqa: F401
    FREEZE_PIECES,
    ORACLE_PIECES,
    SCRIPT_CASE_01,
    SCRIPT_CASE_FIXTURE,
    SCRIPT_CHAIR_02,
    SCRIPT_CHAIR_04,
    SCRIPT_STOOL,
    freeze_tool_calls,
    oracle_tool_calls,
)

__all__ = [
    "ORACLE_PIECES",
    "FREEZE_PIECES",
    "SCRIPT_CASE_01",
    "SCRIPT_CASE_FIXTURE",
    "SCRIPT_CHAIR_02",
    "SCRIPT_CHAIR_04",
    "SCRIPT_STOOL",
    "oracle_tool_calls",
    "freeze_tool_calls",
]
