
import pytest

from core.ipc.client import IPCClient, IPCClientError
from core.ipc.models import Component, MessageType, create_message
from core.ipc.server import IPCServer


def _response_handler(message):
    """Return a correlated response for incoming commands."""
    if message.message_type == MessageType.COMMAND:
        return create_message(
            source=Component.SUPERVISOR,
            target=message.source,
            message_type=MessageType.RESPONSE,
            action=message.action,
            sequence=1,
            correlation_id=message.message_id,
            payload={
                "status": "COMPLETED",
                "echo": message.payload,
            },
        )

    return None


def test_client_connects_and_reports_connection_state(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=_response_handler,
    )
    server.start()

    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    try:
        assert not client.is_connected

        client.connect()

        assert client.is_connected

    finally:
        client.close()
        server.stop()


def test_client_request_response_round_trip(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=_response_handler,
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
            payload={"value": 42},
        )

        assert response.payload["status"] == "COMPLETED"
        assert response.payload["echo"] == {"value": 42}

    finally:
        client.close()
        server.stop()


def test_client_sequence_increments_for_each_message(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=_response_handler,
    )
    server.start()

    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    try:
        client.connect()

        first = client.send(action="FIRST")
        second = client.send(action="SECOND")

        assert first.sequence == 1
        assert second.sequence == 2
        assert client.sequence == 2

    finally:
        client.close()
        server.stop()


def test_client_close_resets_connection_state(socket_path):
    server = IPCServer(
        socket_path=socket_path,
        on_message=_response_handler,
    )
    server.start()

    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    try:
        client.connect()
        client.close()

        assert not client.is_connected

    finally:
        client.close()
        server.stop()


def test_disconnected_client_rejects_send(socket_path):
    client = IPCClient(
        socket_path=socket_path,
        component=Component.WEB_CONTROLLER,
    )

    with pytest.raises(IPCClientError):
        client.send(action="PING")
