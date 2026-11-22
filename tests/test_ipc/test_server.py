import os
import stat
import threading
import time

from core.ipc.models import Component, MessageType, create_message
from core.ipc.server import IPCServer
from core.ipc.client import IPCClient


def _wait_until(predicate, timeout=2.0):
    """Wait until a condition becomes true or the timeout expires."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True

        time.sleep(0.01)

    return False


def test_server_creates_socket_with_restricted_permissions(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=lambda message: None,
    )
    server.start()

    try:
        mode = stat.S_IMODE(os.stat(socket_path).st_mode)

        assert mode == 0o600

    finally:
        server.stop()


def test_server_receives_message_and_returns_response(socket_path):
    received = threading.Event()

    def handler(message):
        received.set()

        return create_message(
            source=Component.SUPERVISOR,
            target=message.source,
            message_type=MessageType.RESPONSE,
            action=message.action,
            sequence=1,
            correlation_id=message.message_id,
            payload={"status": "COMPLETED"},
        )

    server = IPCServer(
        socket_path=socket_path,
        on_message=handler,
    )
    server.start()

    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    try:
        client.connect()

        response = client.request(
            action="PING",
            payload={"probe": True},
        )

        assert received.wait(1.0)
        assert response.payload["status"] == "COMPLETED"

    finally:
        client.close()
        server.stop()


def test_server_accepts_new_connection_with_fresh_sequence(socket_path):
    seen = []

    def handler(message):
        seen.append(message.sequence)
        return None

    server = IPCServer(
        socket_path=socket_path,
        on_message=handler,
    )
    server.start()

    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    try:
        client.connect()

        client.send(action="PING")

        assert _wait_until(lambda: seen == [1])

        # A new connection starts a fresh sequence at one.
        client.close()
        client.connect()

        client.send(action="PING")

        assert _wait_until(lambda: seen == [1, 1])

    finally:
        client.close()
        server.stop()


def test_server_stops_and_removes_its_socket(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=lambda message: None,
    )

    server.start()

    assert os.path.exists(socket_path)

    server.stop()

    assert not os.path.exists(socket_path)
