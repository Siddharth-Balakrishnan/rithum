from datetime import datetime
from uuid import UUID

from core.ipc.models import (
    Component,
    MessageType,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    ResponseStatus,
    create_message,
    local_timestamp,
)


def test_protocol_constants_are_defined():
    assert PROTOCOL_NAME == "rithum-ipc"
    assert PROTOCOL_VERSION == "1.0"


def test_registered_components_include_core_processes():
    expected = {
        "supervisor",
        "web_controller",
        "motion_controller",
        "face_renderer",
        "vision_worker",
        "voice_bridge",
        "diagnostics",
        "hardware_manager",
    }
    assert expected.issubset({component.value for component in Component})


def test_message_types_are_registered():
    expected = {"COMMAND", "RESPONSE", "EVENT", "ERROR", "HEARTBEAT", "STATUS"}
    assert expected.issubset({message_type.value for message_type in MessageType})


def test_response_statuses_are_registered():
    expected = {"RECEIVED", "ACCEPTED", "REJECTED", "COMPLETED", "FAILED"}
    assert expected.issubset({status.value for status in ResponseStatus})


def test_create_message_populates_envelope(valid_message):
    message = valid_message
    assert message.protocol_version == PROTOCOL_VERSION
    assert message.source == Component.WEB_CONTROLLER
    assert message.target == Component.SUPERVISOR
    assert message.message_type == MessageType.COMMAND
    assert message.action == "PING"
    assert message.payload == {"test": True}
    assert isinstance(UUID(message.message_id), UUID)
    assert message.sequence >= 1
    assert message.metadata == {}


def test_message_to_dict_serializes_enum_values(valid_message):
    data = valid_message.to_dict()
    assert data["source"] == "web_controller"
    assert data["target"] == "supervisor"
    assert data["message_type"] == "COMMAND"
    assert data["payload"] == {"test": True}


def test_local_timestamp_contains_timezone_and_milliseconds():
    timestamp = local_timestamp()
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None
    assert "." in timestamp
