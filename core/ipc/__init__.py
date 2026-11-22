
"""Rithum inter-process communication package."""

from .models import (
    Component,
    MessageEnvelope,
    MessageType,
    ResponseStatus,
    create_message,
)

from .validator import (
    MessageValidationError,
    validate_message,
    validate_sequence,
)

from .framing import (
    FramingError,
    encode_frame,
    decode_frame,
    send_frame,
    recv_frame,
)

from .server import (
    IPCServer,
    PeerCredentials,
)

from .client import (
    IPCClient,
    IPCClientError,
)

__all__ = [
    "Component",
    "MessageEnvelope",
    "MessageType",
    "ResponseStatus",
    "create_message",
    "MessageValidationError",
    "validate_message",
    "validate_sequence",
    "FramingError",
    "encode_frame",
    "decode_frame",
    "send_frame",
    "recv_frame",
    "IPCServer",
    "PeerCredentials",
    "IPCClient",
    "IPCClientError",
]
