"""Protocol state machine for B->C->D henshin pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .constants import HAPPY_PATH, REFUSAL_CODES


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _happy_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for idx, state in enumerate(HAPPY_PATH[:-1]):
        nxt = HAPPY_PATH[idx + 1]
        edges.setdefault(state, set()).add(nxt)
    return edges


ALLOWED_TRANSITIONS = _happy_edges()
TERMINAL_STATES = {"ARCHIVED", "REFUSED"}


@dataclass(slots=True)
class ProtocolEvent:
    timestamp: str
    from_state: str
    to_state: str
    status: str
    note: str
    refusal_code: str | None = None


class ProtocolStateMachine:
    """Strict protocol runner.

    The machine enforces legal state changes.
    Refusal is always possible until terminal state is reached.
    """

    def __init__(self, initial_state: str = "IDLE") -> None:
        self.state = initial_state
        self.events: list[ProtocolEvent] = []

    def _record(
        self,
        from_state: str,
        to_state: str,
        *,
        status: str = "OK",
        note: str = "",
        refusal_code: str | None = None,
    ) -> ProtocolEvent:
        event = ProtocolEvent(
            timestamp=_utc_now_iso(),
            from_state=from_state,
            to_state=to_state,
            status=status,
            note=note,
            refusal_code=refusal_code,
        )
        self.events.append(event)
        return event

    def transition(self, to_state: str, note: str = "") -> ProtocolEvent:
        if self.state in TERMINAL_STATES:
            raise ValueError(f"Cannot transition from terminal state: {self.state}")

        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if to_state not in allowed:
            raise ValueError(f"Illegal transition: {self.state} -> {to_state}")

        from_state = self.state
        self.state = to_state
        return self._record(from_state, to_state, status="OK", note=note)

    def refuse(self, code: str, note: str = "") -> ProtocolEvent:
        if self.state in TERMINAL_STATES:
            raise ValueError(f"Cannot refuse from terminal state: {self.state}")
        if code not in REFUSAL_CODES:
            raise ValueError(f"Unknown refusal code: {code}")

        from_state = self.state
        self.state = "REFUSED"
        return self._record(
            from_state,
            "REFUSED",
            status="REFUSED",
            note=note or "Protocol rejected",
            refusal_code=code,
        )

    def run_happy_path(self) -> list[ProtocolEvent]:
        if self.state != "IDLE":
            raise ValueError("run_happy_path requires initial state IDLE.")
        for nxt in HAPPY_PATH[1:]:
            self.transition(nxt)
        return self.events
