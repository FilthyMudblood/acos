"""MCP-behind-Executor sketch (L1).

This is **not** a full MCP client. It models the correct placement:

  Intent → Gateway (APPROVED) → Executor → registry handler → MCP-shaped backend

Incorrect (bypasses governance):

  LLM / orchestrator ──direct──► MCP server

Honesty limits:
  - No real JSON-RPC / stdio MCP transport by default.
  - In-process stub catalog proves wiring and fail-closed placement.
  - L2 would add network/process isolation around the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


ToolFn = Callable[..., Awaitable[Dict[str, Any]]]


@dataclass
class McpToolDescriptor:
    name: str
    description: str = ""
    criticality_hint: float = 0.5


@dataclass
class McpBackendSketch:
    """In-process MCP-shaped tool catalog living *behind* the Executor."""

    server_name: str = "acos-mcp-sketch"
    _tools: Dict[str, ToolFn] = field(default_factory=dict)
    _meta: Dict[str, McpToolDescriptor] = field(default_factory=dict)
    call_log: List[Dict[str, Any]] = field(default_factory=list)

    def register(
        self,
        name: str,
        handler: ToolFn,
        *,
        description: str = "",
        criticality_hint: float = 0.5,
    ) -> None:
        self._tools[name] = handler
        self._meta[name] = McpToolDescriptor(
            name=name,
            description=description,
            criticality_hint=criticality_hint,
        )

    def list_tools(self) -> List[McpToolDescriptor]:
        return [self._meta[n] for n in sorted(self._tools)]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"MCP sketch has no tool named {name!r}")
        args = dict(arguments or {})
        self.call_log.append({"tool": name, "arguments": args})
        result = await self._tools[name](**args)
        return {"server": self.server_name, "tool": name, "result": result}


class McpToolProxy:
    """Adapter: one registry handler that forwards to the MCP sketch.

    Register ``proxy.handler`` (or per-tool wrappers) on ``PhysicalToolRegistry``.
    The Gateway never imports or calls this module; only Executor-dispatched
    handlers may reach the backend.
    """

    def __init__(self, backend: McpBackendSketch, tool_name: str) -> None:
        self.backend = backend
        self.tool_name = tool_name

    async def handler(self, **kwargs: Any) -> Dict[str, Any]:
        return await self.backend.call_tool(self.tool_name, kwargs)
