"""Read-only filesystem connector for L1 realism demos.

The connector may only *read* files under an explicit root. Write / delete /
path-escape attempts raise. Register handlers from this connector on a
``PhysicalToolRegistry`` and invoke them only after Gateway ``APPROVED``
via ``execute_approved``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


class ReadOnlyFsError(Exception):
    """Raised on path escape, missing file, or write-like operations."""


class ReadOnlyFilesystemConnector:
    """Bound a chroot-like root and expose async read helpers."""

    def __init__(self, root: str | os.PathLike[str], *, max_bytes: int = 64_000) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ReadOnlyFsError(f"root is not a directory: {self.root}")
        self.max_bytes = int(max_bytes)

    def _resolve_under_root(self, relative_path: str) -> Path:
        # Reject absolute and parent traversal before resolve.
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ReadOnlyFsError(f"path escape rejected: {relative_path!r}")
        candidate = (self.root / rel).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ReadOnlyFsError(f"path escape rejected: {relative_path!r}") from exc
        return candidate

    async def read_text(self, path: str, *, encoding: str = "utf-8") -> Dict[str, Any]:
        target = self._resolve_under_root(path)
        if not target.is_file():
            raise ReadOnlyFsError(f"not a file: {path}")
        size = target.stat().st_size
        if size > self.max_bytes:
            raise ReadOnlyFsError(f"file exceeds max_bytes={self.max_bytes}: {path}")
        text = target.read_text(encoding=encoding)
        return {
            "path": path,
            "bytes": size,
            "content": text,
            "mode": "read_only",
        }

    async def list_dir(self, path: str = ".") -> Dict[str, Any]:
        target = self._resolve_under_root(path)
        if not target.is_dir():
            raise ReadOnlyFsError(f"not a directory: {path}")
        names = sorted(p.name for p in target.iterdir())
        return {"path": path, "entries": names, "mode": "read_only"}

    async def write_text(self, path: str, content: str) -> Dict[str, Any]:
        # Explicitly present so registry wiring cannot accidentally grant writes.
        raise ReadOnlyFsError("write_text is forbidden on ReadOnlyFilesystemConnector")

    def as_tool_handlers(self) -> Dict[str, Any]:
        """Map tool names → async callables for PhysicalToolRegistry."""
        return {
            "fs_read_text": self.read_text,
            "fs_list_dir": self.list_dir,
        }
