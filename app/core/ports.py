"""Core ports that define boundary contracts for infrastructure adapters."""

from __future__ import annotations

from typing import Protocol


class DatabaseReadinessPort(Protocol):
    """Contract for probing database readiness from the core layer."""

    def ping(self) -> tuple[bool, str | None]:
        """Return (is_ready, detail)."""
