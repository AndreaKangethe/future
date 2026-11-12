"""Grounding primitives shared by assistant providers.

The registry deliberately accepts read-only tools only.  Keeping this boundary
small makes it possible to use the assistant without giving an LLM write
access to the application database.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any


class CitationValidationError(ValueError):
    """Raised when an assistant cites evidence that was not supplied or allowed."""


PermissionCallback = Callable[[str, Mapping[str, Any]], bool | Awaitable[bool]]
ToolHandler = Callable[[Mapping[str, Any]], Any | Awaitable[Any]]
READ_ONLY_TOOL_NAMES = frozenset(
    {
        "get_asset",
        "search_assets",
        "get_asset_history",
        "get_observations",
        "get_services_exposure",
        "get_vulnerabilities",
        "get_findings",
        "get_relationships",
        "get_blast_radius",
        "get_risk_assessment",
        "get_risk_diff",
        "list_recent_changes",
        "list_anomalies",
        "get_investigation",
        "explain_finding",
    }
)


@dataclass(frozen=True)
class ReadOnlyTool:
    name: str
    description: str
    handler: ToolHandler
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    read_only: bool = True


class ReadOnlyToolRegistry:
    """Registry for explicitly permitted, read-only assistant tools."""

    def __init__(self, permission: PermissionCallback | None = None):
        self._permission = permission
        self._tools: dict[str, ReadOnlyTool] = {}

    def register(self, tool: ReadOnlyTool) -> ReadOnlyTool:
        if not tool.read_only:
            raise ValueError("Assistant tools must be read-only")
        if tool.name not in READ_ONLY_TOOL_NAMES:
            raise ValueError(f"Tool is not in the read-only allowlist: {tool.name}")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> ReadOnlyTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown assistant tool: {name}") from exc

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": dict(tool.input_schema),
            }
            for tool in self._tools.values()
        ]

    async def invoke(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        args = arguments or {}
        tool = self.get(name)
        if self._permission is not None:
            try:
                parameter_count = len(inspect.signature(self._permission).parameters)
            except (TypeError, ValueError):
                parameter_count = 2
            permitted = (
                self._permission(name) if parameter_count < 2 else self._permission(name, args)
            )
            if inspect.isawaitable(permitted):
                permitted = await permitted
            if not permitted:
                raise PermissionError(f"Assistant tool denied: {name}")
        result = tool.handler(args)
        return await result if inspect.isawaitable(result) else result


def _citation_key(citation: Mapping[str, Any]) -> tuple[str, str] | None:
    record_type = citation.get("record_type", citation.get("type"))
    record_id = citation.get("record_id", citation.get("id"))
    if record_type is None or record_id is None:
        return None
    return str(record_type), str(record_id)


def validate_citations(
    citations: Iterable[Mapping[str, Any]],
    evidence: Iterable[Mapping[str, Any] | Any],
    permission: Callable[[str, str], bool] | None = None,
) -> list[dict[str, str]]:
    """Return normalized citations that point at supplied, accessible evidence."""

    available: set[tuple[str, str]] = set()
    for item in evidence:
        if isinstance(item, Mapping):
            key = _citation_key(item)
        else:
            key = (str(getattr(item, "record_type", "")), str(getattr(item, "record_id", "")))
        if key and all(key):
            available.add(key)

    valid: list[dict[str, str]] = []
    for citation in citations:
        key = _citation_key(citation)
        if key is None or key not in available:
            raise CitationValidationError(f"Unknown citation: {citation!r}")
        if permission is not None and not permission(*key):
            raise CitationValidationError(f"Unauthorized citation: {key[0]}:{key[1]}")
        valid.append({"type": key[0], "id": key[1]})
    return valid


def format_sse(
    event: str,
    data: Any,
    *,
    event_id: str | None = None,
    retry: int | None = None,
) -> str:
    """Format one standards-compliant SSE event, including JSON data."""

    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    if event:
        lines.append(f"event: {event}")
    if retry is not None:
        lines.append(f"retry: {retry}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    lines.extend(f"data: {line}" for line in payload.splitlines() or [""])
    return "\n".join(lines) + "\n\n"


def sse_events(events: Iterable[tuple[str, Any]]) -> Iterable[str]:
    for event, data in events:
        yield format_sse(event, data)
