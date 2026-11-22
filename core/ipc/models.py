
"""Shared message models and protocol definitions for Rithum IPC."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

PROTOCOL_NAME = "rithum-ipc"
PROTOCOL_VERSION = "1.0"

MAX_MESSAGE_SIZE = 64 * 1024  # 64 KiB


# ---------------------------------------------------------------------------
# Registered IPC components
# ---------------------------------------------------------------------------

class Component(StrEnum):
    """Components permitted to communicate through the IPC layer."""

    SUPERVISOR = "supervisor"
    WEB_CONTROLLER = "web_controller"
    MOTION_CONTROLLER = "motion_controller"
    FACE_RENDERER = "face_renderer"
    VISION_WORKER = "vision_worker"
    VOICE_BRIDGE = "voice_bridge"
    DIAGNOSTICS = "diagnostics"
    HARDWARE_MANAGER = "hardware_manager"


# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MessageType(StrEnum):
    """Supported IPC message categories."""

    COMMAND = "COMMAND"
    RESPONSE = "RESPONSE"
    EVENT = "EVENT"
    ERROR = "ERROR"
    HEARTBEAT = "HEARTBEAT"
    STATUS = "STATUS"


# ---------------------------------------------------------------------------
# Response statuses
# ---------------------------------------------------------------------------

class ResponseStatus(StrEnum):
    """Lifecycle status of a received command."""

    RECEIVED = "RECEIVED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Message envelope
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MessageEnvelope:
    """
    Standard envelope for all Rithum IPC messages.

    The envelope is intentionally independent of individual command
    payloads. Action-specific payload validation belongs in validator.py.
    """

    protocol_version: str
    message_id: str
    correlation_id: str | None
    sequence: int
    source: str
    target: str
    message_type: MessageType
    action: str
    payload: dict[str, Any]
    metadata: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the envelope into a JSON-serializable dictionary."""

        return {
            "protocol_version": self.protocol_version,
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "sequence": self.sequence,
            "source": self.source,
            "target": self.target,
            "message_type": self.message_type.value,
            "action": self.action,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Message factory
# ---------------------------------------------------------------------------

def local_timestamp() -> str:
    """
    Return the system's local time as an ISO 8601 timestamp.

    The timezone offset is obtained from the operating system.
    No timezone offset is hardcoded.
    """

    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def create_message(
    *,
    source: Component | str,
    target: Component | str,
    message_type: MessageType,
    action: str,
    sequence: int,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> MessageEnvelope:
    """
    Construct a new IPC message envelope.

    Validation of component permissions, sequence numbers, payloads,
    timestamps and authorization is performed separately.
    """

    return MessageEnvelope(
        protocol_version=PROTOCOL_VERSION,
        message_id=str(uuid4()),
        correlation_id=correlation_id,
        sequence=sequence,
        source=str(source),
        target=str(target),
        message_type=message_type,
        action=action,
        payload={} if payload is None else payload,
        metadata={} if metadata is None else metadata,
        timestamp=local_timestamp(),
    )
