
import socket
import struct

import pytest

from core.ipc.framing import (
    HEADER_SIZE,
    FramingError,
    decode_frame,
    encode_frame,
    recv_frame,
    send_frame,
)


def test_frame_encoding_adds_four_byte_big_endian_length(valid_message):
    frame = encode_frame(valid_message.to_dict())

    payload_length = struct.unpack(
        "!I",
        frame[:HEADER_SIZE],
    )[0]

    assert payload_length == len(frame) - HEADER_SIZE


def test_frame_round_trip(valid_message):
    frame = encode_frame(valid_message.to_dict())

    # decode_frame expects the complete frame, including its header.
    decoded = decode_frame(frame)

    assert decoded == valid_message.to_dict()


def test_socket_send_and_receive(valid_message):
    left, right = socket.socketpair()

    try:
        send_frame(left, valid_message.to_dict())
        received = recv_frame(right)

        assert received == valid_message.to_dict()

    finally:
        left.close()
        right.close()


def test_empty_frame_payload_is_rejected():
    with pytest.raises(FramingError):
        decode_frame(b"")


def test_invalid_json_is_rejected():
    with pytest.raises(FramingError):
        decode_frame(struct.pack("!I", 14) + b"{invalid-json")


def test_incomplete_header_is_rejected():
    left, right = socket.socketpair()

    try:
        left.sendall(b"\x00\x00")
        left.close()

        with pytest.raises(ConnectionError):
            recv_frame(right)

    finally:
        left.close()
        right.close()


def test_incomplete_payload_is_rejected():
    left, right = socket.socketpair()

    try:
        left.sendall(struct.pack("!I", 8) + b"{}")
        left.close()

        with pytest.raises(ConnectionError):
            recv_frame(right)

    finally:
        left.close()
        right.close()
