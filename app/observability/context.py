"""Request-scoped observability context helpers."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Final, cast


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Bounded request metadata propagated through logs and audit events."""

    request_id: str | None = None
    http_method: str | None = None
    http_route: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    client_ip: str | None = None
    user_agent: str | None = None
    surface: str | None = None
    outcome: str | None = None
    error_code: str | None = None
    exception_type: str | None = None


_UNSET: Final = object()
_REQUEST_CONTEXT: ContextVar[RequestContext | None] = ContextVar(
    "request_context",
    default=None,
)


def get_request_context() -> RequestContext:
    """Return the current request context for the active execution context."""
    context = _REQUEST_CONTEXT.get()
    return RequestContext() if context is None else context


def set_request_context(
    *,
    request_id: str | None | object = _UNSET,
    http_method: str | None | object = _UNSET,
    http_route: str | None | object = _UNSET,
    status_code: int | None | object = _UNSET,
    duration_ms: float | None | object = _UNSET,
    client_ip: str | None | object = _UNSET,
    user_agent: str | None | object = _UNSET,
    surface: str | None | object = _UNSET,
    outcome: str | None | object = _UNSET,
    error_code: str | None | object = _UNSET,
    exception_type: str | None | object = _UNSET,
) -> None:
    """Update the request context, preserving omitted fields."""
    current = get_request_context()
    _REQUEST_CONTEXT.set(
        RequestContext(
            request_id=(
                current.request_id if request_id is _UNSET else cast("str | None", request_id)
            ),
            http_method=(
                current.http_method if http_method is _UNSET else cast("str | None", http_method)
            ),
            http_route=(
                current.http_route if http_route is _UNSET else cast("str | None", http_route)
            ),
            status_code=(
                current.status_code if status_code is _UNSET else cast("int | None", status_code)
            ),
            duration_ms=(
                current.duration_ms if duration_ms is _UNSET else cast("float | None", duration_ms)
            ),
            client_ip=(current.client_ip if client_ip is _UNSET else cast("str | None", client_ip)),
            user_agent=(
                current.user_agent if user_agent is _UNSET else cast("str | None", user_agent)
            ),
            surface=(current.surface if surface is _UNSET else cast("str | None", surface)),
            outcome=(current.outcome if outcome is _UNSET else cast("str | None", outcome)),
            error_code=(
                current.error_code if error_code is _UNSET else cast("str | None", error_code)
            ),
            exception_type=(
                current.exception_type
                if exception_type is _UNSET
                else cast("str | None", exception_type)
            ),
        )
    )


def clear_request_context() -> None:
    """Reset request-scoped observability values."""
    _REQUEST_CONTEXT.set(RequestContext())
