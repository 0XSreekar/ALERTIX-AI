"""State and severity contracts for realtime hazard processing."""

from __future__ import annotations

from enum import StrEnum


class ProcessingState(StrEnum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    VALIDATED = "VALIDATED"
    ROUTED = "ROUTED"
    ALERTED = "ALERTED"
    STORED = "STORED"
    RETRY = "RETRY"
    DEAD_LETTER = "DEAD_LETTER"


class AlertTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


STATE_ORDER: tuple[ProcessingState, ...] = (
    ProcessingState.NEW,
    ProcessingState.PROCESSING,
    ProcessingState.VALIDATED,
    ProcessingState.ROUTED,
    ProcessingState.ALERTED,
    ProcessingState.STORED,
)


class InvalidStateTransitionError(ValueError):
    """Raised when a processing state moves out of order."""


def assert_next_state(current: ProcessingState, next_state: ProcessingState) -> None:
    if next_state in {ProcessingState.RETRY, ProcessingState.DEAD_LETTER}:
        return
    if current in {ProcessingState.RETRY, ProcessingState.DEAD_LETTER}:
        if next_state == ProcessingState.PROCESSING:
            return
        raise InvalidStateTransitionError(f"cannot move from {current} to {next_state}")
    try:
        current_index = STATE_ORDER.index(current)
        next_index = STATE_ORDER.index(next_state)
    except ValueError as exc:
        raise InvalidStateTransitionError(f"unknown transition {current} -> {next_state}") from exc
    if next_index != current_index + 1:
        raise InvalidStateTransitionError(f"expected {STATE_ORDER[current_index + 1]}, got {next_state}")
