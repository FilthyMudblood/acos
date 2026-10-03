"""Realism connectors: tool backends that sit *behind* the Runtime Executor.

L1 honesty: these modules demonstrate physical I/O and MCP-shaped backends
reachable only via ``PhysicalToolRegistry`` handlers after ``APPROVED``.
They do **not** provide L2 process/network isolation.
"""

from .mcp_backend import McpBackendSketch, McpToolProxy
from .readonly_fs import ReadOnlyFilesystemConnector, ReadOnlyFsError

__all__ = [
    "McpBackendSketch",
    "McpToolProxy",
    "ReadOnlyFilesystemConnector",
    "ReadOnlyFsError",
]
