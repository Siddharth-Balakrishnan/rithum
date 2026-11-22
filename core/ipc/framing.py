
"""Length-prefixed JSON framing for Rithum IPC."""

from __future__ import annotations

import json
import socket
import struct

from collections.abc import Mapping
from typing import Any

from .models import MAX_MESSAGE_SIZE, MessageEnvelope


# ---------------------------------------------------------------------------
# Frame definitions
# ---------------------------------------------------------------------------

HEADER_SIZE = 4
HEADER_FORMAT = "!I"  # Unsigned 32-bit integer, network byte order.

MAX_FRAME_SIZE = HEADER_SIZE + MAX_MESSAGE_SIZE


# ---------------------------------------------------------------------------
# Framing exception
# ---------------------------------------------------------------------------

class FramingError(ValueError):
    """Raised when an IPC frame cannot be encoded or decoded."""


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize_message(
    message: MessageEnvelope | Mapping[str, Any],
) -> bytes:
    """Convert a message into compact UTF-8 JSON bytes."""

    if isinstance(message, MessageEnvelope):
        data = message.to_dict()
    elif isinstance(message, Mapping):
        data = dict(message)
    else:
        raise FramingError(
            "Message must be a MessageEnvelope or mapping."
        )

    try:
        serialized = json.dumps(
            data,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        raise FramingError(
            "Message contains values that cannot be serialized as JSON."
        ) from None

    if not serialized:
        raise FramingError("Message payload cannot be empty.")

    if len(serialized) > MAX_MESSAGE_SIZE:
        raise FramingError(
            f"Message exceeds the {MAX_MESSAGE_SIZE}-byte limit."
        )

    return serialized


# ---------------------------------------------------------------------------
# Frame encoding
# ---------------------------------------------------------------------------

def encode_frame(
    message: MessageEnvelope | Mapping[str, Any],
) -> bytes:
    """
    Encode a message into a length-prefixed IPC frame.

    Frame structure:
        [4-byte unsigned big-endian length][UTF-8 JSON payload]
    """

    payload = _serialize_message(message)

    header = struct.pack(
        HEADER_FORMAT,
        len(payload),
    )

    return header + payload


# ---------------------------------------------------------------------------
# Frame decoding
# ---------------------------------------------------------------------------

def decode_frame(frame: bytes) -> dict[str, Any]:
    """
    Decode one complete IPC frame into a Python dictionary.

    This function expects exactly one complete frame.
    It does not perform protocol-level message validation.
    """

    if not isinstance(frame, bytes):
        raise FramingError("Frame must be bytes.")

    if len(frame) < HEADER_SIZE:
        raise FramingError("Incomplete frame header.")

    payload_length = struct.unpack(
        HEADER_FORMAT,
        frame[:HEADER_SIZE],
    )[0]

    if payload_length == 0:
        raise FramingError("Frame payload cannot be empty.")

    if payload_length > MAX_MESSAGE_SIZE:
        raise FramingError(
            f"Frame exceeds the {MAX_MESSAGE_SIZE}-byte limit."
        )

    expected_length = HEADER_SIZE + payload_length

    if len(frame) != expected_length:
        raise FramingError(
            f"Frame length mismatch: expected {expected_length} bytes, "
            f"received {len(frame)} bytes."
        )

    payload = frame[HEADER_SIZE:]

    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError:
        raise FramingError(
            "Frame payload is not valid UTF-8."
        ) from None

    try:
        data = json.loads(
            decoded,
            parse_constant=lambda value: (
                _raise_invalid_json_constant(value)
            ),
        )
    except (json.JSONDecodeError, ValueError, RecursionError):
        raise FramingError(
            "Frame payload contains invalid JSON."
        ) from None

    if not isinstance(data, dict):
        raise FramingError(
            "Decoded IPC message must be a JSON object."
        )

    return data


def _raise_invalid_json_constant(value: str) -> None:
    """Reject non-standard JSON constants such as NaN and Infinity."""

    raise ValueError(f"Invalid JSON constant: {value}")


# ---------------------------------------------------------------------------
# Socket helpers
# ---------------------------------------------------------------------------

def _recv_exact(sock: socket.socket, size: int) -> bytes:
    """
    Receive exactly the requested number of bytes.

    A socket may return fewer bytes than requested, so repeated reads
    are required.
    """

    chunks = bytearray()

    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))

        if not chunk:
            raise ConnectionError(
                "Connection closed before the complete frame was received."
            )

        chunks.extend(chunk)

    return bytes(chunks)


def send_frame(
    sock: socket.socket,
    message: MessageEnvelope | Mapping[str, Any],
) -> None:
    """Encode and send one complete IPC frame."""

    frame = encode_frame(message)
    sock.sendall(frame)


def recv_frame(sock: socket.socket) -> dict[str, Any]:
    """
    Receive and decode one complete IPC frame from a socket.

    The header is read first, followed by the exact payload length.
    """

    header = _recv_exact(sock, HEADER_SIZE)

    payload_length = struct.unpack(
        HEADER_FORMAT,
        header,
    )[0]

    if payload_length == 0:
        raise FramingError("Frame payload cannot be empty.")

    if payload_length > MAX_MESSAGE_SIZE:
        raise FramingError(
            f"Frame exceeds the {MAX_MESSAGE_SIZE}-byte limit."
        )

    payload = _recv_exact(sock, payload_length)

    return decode_frame(header + payload)
