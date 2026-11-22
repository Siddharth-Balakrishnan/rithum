
"""Shared fixtures for Rithum IPC tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.ipc.models import Component, MessageType, create_message


@pytest.fixture
def socket_path():
    """Return an isolated Unix-domain socket path for one test."""
    with tempfile.TemporaryDirectory(prefix="rithum-ipc-test-") as directory:
        yield str(Path(directory) / "rithum.sock")


@pytest.fixture
def valid_message():
    """Return a valid IPC command envelope."""
    return create_message(
        source=Component.WEB_CONTROLLER,
        target=Component.SUPERVISOR,
        message_type=MessageType.COMMAND,
        action="PING",
        sequence=1,
        payload={"test": True},
    )
