from dataclasses import dataclass
from typing import Any


class IntelligenceLoadError(RuntimeError):
    """A source could not be retrieved or decoded."""


@dataclass(frozen=True)
class LoadResult:
    source: str
    records: list[dict[str, Any]]
    used_fallback: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None
