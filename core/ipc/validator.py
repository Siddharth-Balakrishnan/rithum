
"""Validation utilities for the Rithum IPC protocol."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from .models import (
    MAX_MESSAGE_SIZE,
    PROTOCOL_VERSION,
    Component,
    MessageEnvelope,
    MessageType,
)


# ---------------------------------------------------------------------------
# Protocol definitions
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "protocol_version",
    "message_id",
    "correlation_id",
    "sequence",
    "source",
    "target",
    "message_type",
    "action",
    "payload",
    "metadata",
    "timestamp",
}

REGISTERED_COMPONENTS = {component.value for component in Component}

BROADCAST_TARGET = "broadcast"

ACTION_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")

TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T"
    r"\d{2}:\d{2}:\d{2}\.\d{3}"
    r"[+-]\d{2}:\d{2}$"
)


# ---------------------------------------------------------------------------
# Validation exception
# ---------------------------------------------------------------------------

class MessageValidationError(ValueError):
    """Raised when an IPC message violates the protocol."""


# ---------------------------------------------------------------------------
# Individual validation helpers
# ---------------------------------------------------------------------------

def _require_string(value: Any, field: str) -> str:
    """Validate a non-empty string field."""

    if not isinstance(value, str) or not value.strip():
        raise MessageValidationError(
            f"'{field}' must be a non-empty string."
        )

    return value


def _validate_uuid(value: Any, field: str) -> None:
    """Validate a UUID string."""

    if not isinstance(value, str):
        raise MessageValidationError(
            f"'{field}' must be a UUID string."
        )

    try:
        UUID(value)
    except (ValueError, AttributeError):
        raise MessageValidationError(
            f"'{field}' contains an invalid UUID."
        ) from None


def _validate_timestamp(value: Any) -> None:
    """Validate an ISO 8601 timestamp with milliseconds and timezone."""

    if not isinstance(value, str):
        raise MessageValidationError(
            "'timestamp' must be a string."
        )

    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise MessageValidationError(
            "'timestamp' must use ISO 8601 format with milliseconds "
            "and an explicit timezone offset."
        )

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise MessageValidationError(
            "'timestamp' is not a valid date and time."
        ) from None

    if parsed.utcoffset() is None:
        raise MessageValidationError(
            "'timestamp' must contain a timezone offset."
        )


def _validate_json_object(value: Any, field: str) -> None:
    """Ensure a field is a JSON-compatible object."""

    if not isinstance(value, dict):
        raise MessageValidationError(
            f"'{field}' must be a JSON object."
        )

    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError):
        raise MessageValidationError(
            f"'{field}' contains values that are not JSON-compatible."
        ) from None


# ---------------------------------------------------------------------------
# Sequence validation
# ---------------------------------------------------------------------------

def validate_sequence(
    sequence: Any,
    *,
    last_sequence: int | None = None,
) -> None:
    """
    Validate a message sequence number.

    If last_sequence is provided, the incoming sequence must be exactly
    the next expected value.

    The caller is responsible for storing and updating sequence state
    separately for each sender process session.
    """

    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise MessageValidationError(
            "'sequence' must be an integer."
        )

    if sequence < 1:
        raise MessageValidationError(
            "'sequence' must be greater than zero."
        )

    if last_sequence is not None:
        if (
            isinstance(last_sequence, bool)
            or not isinstance(last_sequence, int)
            or last_sequence < 0
        ):
            raise MessageValidationError(
                "'last_sequence' must be a non-negative integer."
            )

        expected = last_sequence + 1

        if sequence != expected:
            raise MessageValidationError(
                f"Invalid sequence number: expected {expected}, "
                f"received {sequence}."
            )


# ---------------------------------------------------------------------------
# Main message validator
# ---------------------------------------------------------------------------

def validate_message(
    data: Any,
    *,
    expected_source: str | None = None,
    last_sequence: int | None = None,
) -> MessageEnvelope:
    """
    Validate a decoded IPC message and convert it into a MessageEnvelope.

    Args:
        data:
            Dictionary obtained from decoding an IPC JSON message.

        expected_source:
            Optional source identity established by the transport layer.
            If supplied, the message source must match it.

        last_sequence:
            Last accepted sequence number for this sender session.

    Returns:
        A validated MessageEnvelope.

    Raises:
        MessageValidationError:
            If any protocol requirement is violated.
    """

    # 1. Validate the top-level structure.

    if not isinstance(data, dict):
        raise MessageValidationError(
            "IPC message must be a JSON object."
        )

    missing_fields = REQUIRED_FIELDS - data.keys()
    unknown_fields = data.keys() - REQUIRED_FIELDS

    if missing_fields:
        raise MessageValidationError(
            f"Missing required fields: {sorted(missing_fields)}."
        )

    if unknown_fields:
        raise MessageValidationError(
            f"Unknown message fields: {sorted(unknown_fields)}."
        )

    # 2. Validate serialized message size.

    try:
        serialized = json.dumps(
            data,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise MessageValidationError(
            "Message contains invalid JSON values."
        ) from None

    if len(serialized) > MAX_MESSAGE_SIZE:
        raise MessageValidationError(
            f"Message exceeds the {MAX_MESSAGE_SIZE}-byte limit."
        )

    # 3. Validate protocol version.

    if data["protocol_version"] != PROTOCOL_VERSION:
        raise MessageValidationError(
            f"Unsupported protocol version: "
            f"{data['protocol_version']!r}."
        )

    # 4. Validate message identifiers.

    _validate_uuid(data["message_id"], "message_id")

    correlation_id = data["correlation_id"]

    if correlation_id is not None:
        _validate_uuid(correlation_id, "correlation_id")

    # 5. Validate sequence number.

    validate_sequence(
        data["sequence"],
        last_sequence=last_sequence,
    )

    # 6. Validate source and target components.

    source = _require_string(data["source"], "source")
    target = _require_string(data["target"], "target")

    if source not in REGISTERED_COMPONENTS:
        raise MessageValidationError(
            f"Unregistered source component: {source!r}."
        )

    if target not in REGISTERED_COMPONENTS and target != BROADCAST_TARGET:
        raise MessageValidationError(
            f"Unregistered target component: {target!r}."
        )

    # 7. Compare claimed source with transport identity when available.

    if expected_source is not None:
        if source != expected_source:
            raise MessageValidationError(
                f"Source identity mismatch: expected "
                f"{expected_source!r}, received {source!r}."
            )

    # 8. Validate message type.

    try:
        message_type = MessageType(data["message_type"])
    except (ValueError, TypeError):
        raise MessageValidationError(
            f"Unsupported message type: {data['message_type']!r}."
        ) from None

    # 9. Broadcast is only permitted for events.

    if target == BROADCAST_TARGET and message_type != MessageType.EVENT:
        raise MessageValidationError(
            "Broadcast messages must use the EVENT message type."
        )

    # 10. Validate action.

    action = _require_string(data["action"], "action")

    if not ACTION_PATTERN.fullmatch(action):
        raise MessageValidationError(
            "'action' must contain uppercase letters, numbers, "
            "and underscores, and begin with a letter."
        )

    # 11. Validate payload and metadata.

    _validate_json_object(data["payload"], "payload")
    _validate_json_object(data["metadata"], "metadata")

    # 12. Validate timestamp.

    _validate_timestamp(data["timestamp"])

    # 13. Construct the validated envelope.

    return MessageEnvelope(
        protocol_version=data["protocol_version"],
        message_id=data["message_id"],
        correlation_id=correlation_id,
        sequence=data["sequence"],
        source=source,
        target=target,
        message_type=message_type,
        action=action,
        payload=data["payload"],
        metadata=data["metadata"],
        timestamp=data["timestamp"],
    )
