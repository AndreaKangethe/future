import pytest

from app.assistant.fallback import Evidence
from app.assistant.grounding import (
    CitationValidationError,
    ReadOnlyTool,
    ReadOnlyToolRegistry,
    format_sse,
    validate_citations,
)
from app.assistant.provider import (
    AnthropicProvider,
    AssistantRequest,
    DeterministicFallbackProvider,
)


@pytest.mark.asyncio
async def test_offline_provider_is_deterministic_and_grounded():
    request = AssistantRequest(
        "What is exposed?",
        (Evidence("asset", "a1", "app-server-01 is internet-facing.", "observed"),),
    )
    response = await DeterministicFallbackProvider().complete(request)
    assert response.provider == "offline"
    assert response.citations == [{"type": "asset", "id": "a1"}]
    assert "app-server-01" in response.answer


@pytest.mark.asyncio
async def test_registry_checks_permission_and_rejects_writes():
    registry = ReadOnlyToolRegistry(lambda name, args: name == "get_asset")
    registry.register(ReadOnlyTool("get_asset", "Get an asset", lambda args: ["a1"]))
    with pytest.raises(ValueError):
        registry.register(ReadOnlyTool("delete", "Delete data", lambda args: None, read_only=False))
    assert await registry.invoke("get_asset") == ["a1"]
    denied = ReadOnlyToolRegistry(lambda name, args: False)
    denied.register(ReadOnlyTool("get_asset", "Get an asset", lambda args: []))
    with pytest.raises(PermissionError):
        await denied.invoke("get_asset")


def test_citations_are_post_validated_and_sse_is_json():
    evidence = [Evidence("finding", "f1", "A finding", "observed")]
    assert validate_citations([{"type": "finding", "id": "f1"}], evidence) == [
        {"type": "finding", "id": "f1"}
    ]
    with pytest.raises(CitationValidationError):
        validate_citations([{"type": "finding", "id": "missing"}], evidence)
    assert format_sse("token", {"text": "hello"}) == 'event: token\ndata: {"text":"hello"}\n\n'


@pytest.mark.asyncio
async def test_anthropic_provider_uses_injected_client():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "Grounded answer"}]}

    class Client:
        def __init__(self):
            self.calls = []

        async def post(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return Response()

    client = Client()
    result = await AnthropicProvider("secret", http_client=client).complete(
        AssistantRequest("Question", ())
    )
    assert result.answer == "Grounded answer"
    assert client.calls[0][1]["headers"]["x-api-key"] == "secret"
