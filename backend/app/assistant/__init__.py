"""Evidence-grounded assistant services."""

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
    AssistantResponse,
    DeterministicFallbackProvider,
    offline_or_anthropic,
)

__all__ = [
    "AnthropicProvider",
    "AssistantRequest",
    "AssistantResponse",
    "CitationValidationError",
    "DeterministicFallbackProvider",
    "ReadOnlyTool",
    "ReadOnlyToolRegistry",
    "format_sse",
    "offline_or_anthropic",
    "validate_citations",
]
