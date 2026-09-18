from __future__ import annotations

from dataclasses import dataclass, field

from .errors import SpecError


@dataclass
class IdRegistry:
    """Deterministic object and target ID registry."""

    _next: dict[str, int] = field(default_factory=dict)
    _targets: dict[str, int] = field(default_factory=dict)

    def allocate(self, kind: str, preferred: str | None = None) -> int:
        if preferred:
            if preferred in self._targets:
                raise SpecError(f"Duplicate reference name: {preferred}")
            value = self._next.get(kind, 1)
            self._next[kind] = value + 1
            self._targets[preferred] = value
            return value
        value = self._next.get(kind, 1)
        self._next[kind] = value + 1
        return value

    def register_target(self, name: str, kind: str = "target") -> int:
        if not name or not isinstance(name, str):
            raise SpecError("A reference name must be a non-empty string.")
        return self.allocate(kind, name)

    def require_target(self, name: str) -> int:
        try:
            return self._targets[name]
        except KeyError as exc:
            raise SpecError(f"Reference target does not exist: {name}") from exc

    @property
    def targets(self) -> dict[str, int]:
        return dict(self._targets)
