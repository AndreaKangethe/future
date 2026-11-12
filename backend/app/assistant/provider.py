"""Provider abstraction for evidence-grounded assistant answers."""

from __future__ import annotations

import inspect
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.assistant.fallback import Evidence, summarize
from app.assistant.grounding import validate_citations


@dataclass(frozen=True)
class AssistantRequest:
    question: str
    evidence: tuple[Evidence, ...] = ()
    tools: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class AssistantResponse:
    answer: str
    citations: list[dict[str, str]] = field(default_factory=list)
    provider: str = "offline"
    limitations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "references": self.citations,
            "limitations": self.limitations,
            "provider": self.provider,
        }


class AssistantProvider(Protocol):
    async def complete(self, request: AssistantRequest) -> AssistantResponse: ...


class DeterministicFallbackProvider:
    """Provider that never uses a network and produces reproducible answers."""

    async def complete(self, request: AssistantRequest) -> AssistantResponse:
        result = summarize(request.question, request.evidence)
        return AssistantResponse(
            answer=result["answer"],
            citations=result["references"],
            provider="offline",
            limitations=result["limitations"],
        )


class AnthropicProvider:
    """Small SDK-free Anthropic Messages client with injectable HTTP transport."""

    def __init__(
        self,
        api_key: str,
        *,
        http_client: Any | None = None,
        model: str = "claude-3-5-sonnet-latest",
        endpoint: str = "https://api.anthropic.com/v1/messages",
        timeout: float = 30.0,
    ):
        if not api_key:
            raise ValueError("Anthropic API key is required")
        self.api_key = api_key
        self.http_client = http_client
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout

    async def complete(self, request: AssistantRequest) -> AssistantResponse:
        evidence = [
            {
                "record_type": item.record_type,
                "record_id": item.record_id,
                "epistemic_class": item.epistemic_class,
                "statement": item.statement,
            }
            for item in request.evidence
        ]
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "system": (
                "Answer only from the supplied evidence. Cite every claim using "
                "record_type:record_id. Say when evidence is missing."
            ),
            "messages": [
                {
                    "role": "user",
                    "content": f"Question: {request.question}\nEvidence: {evidence}",
                }
            ],
        }
        response = await self._post(body)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        payload = response.json() if hasattr(response, "json") else response
        if inspect.isawaitable(payload):
            payload = await payload
        answer = "".join(
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        )
        raw_citations = payload.get("citations", [])
        citations = validate_citations(raw_citations, request.evidence) if raw_citations else []
        return AssistantResponse(
            answer=answer,
            citations=citations,
            provider="anthropic",
            limitations=[] if citations else ["The provider returned no verifiable citations."],
        )

    async def _post(self, body: Mapping[str, Any]) -> Any:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if self.http_client is not None:
            result = self.http_client.post(
                self.endpoint, headers=headers, json=body, timeout=self.timeout
            )
            return await result if inspect.isawaitable(result) else result
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.post(self.endpoint, headers=headers, json=body)


def offline_or_anthropic(
    api_key: str | None,
    *,
    http_client: Any | None = None,
    model: str = "claude-3-5-sonnet-latest",
) -> AssistantProvider:
    if api_key:
        return AnthropicProvider(api_key, http_client=http_client, model=model)
    return DeterministicFallbackProvider()


def evidence_tuple(evidence: Iterable[Evidence]) -> tuple[Evidence, ...]:
    return tuple(evidence)
