from copy import deepcopy

import pytest

from core.ipc.models import Component, MessageType
from core.ipc.validator import MessageValidationError, validate_message


def test_valid_message_is_accepted(valid_message):
    validate_message(valid_message.to_dict())


def test_invalid_uuid_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["message_id"] = "not-a-uuid"
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_unknown_component_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["source"] = "unknown_worker"
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_expected_source_mismatch_is_rejected(valid_message):
    with pytest.raises(MessageValidationError):
        validate_message(
            valid_message.to_dict(),
            expected_source=Component.DIAGNOSTICS,
        )


def test_non_increasing_sequence_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["sequence"] = 2
    with pytest.raises(MessageValidationError):
        validate_message(data, last_sequence=2)


def test_broadcast_command_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["target"] = "broadcast"
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_missing_required_field_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data.pop("action")
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_unknown_field_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["unexpected"] = "not allowed"
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_invalid_payload_type_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["payload"] = ["not", "an", "object"]
    with pytest.raises(MessageValidationError):
        validate_message(data)


def test_lowercase_action_is_rejected(valid_message):
    data = deepcopy(valid_message.to_dict())
    data["action"] = "move_forward"
    with pytest.raises(MessageValidationError):
        validate_message(data)
