"""Tests for Rithum application configuration."""

import os
import unittest
from unittest.mock import patch

from core.config import load_config


class TestRithumConfig(unittest.TestCase):

    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_default_configuration(self):
        config = load_config()

        self.assertEqual(config.robot.name, "Rithum")
        self.assertEqual(config.robot.hostname, "r1t-hum")
        self.assertEqual(config.runtime.environment, "development")
        self.assertEqual(config.runtime.log_level, "INFO")

    def test_motors_disabled_by_default(self):
        config = load_config()

        self.assertFalse(config.hardware.motors_enabled)

    def test_ir_sensors_disabled_by_default(self):
        config = load_config()

        self.assertFalse(config.hardware.ir_sensors_enabled)

    def test_autonomy_disabled_by_default(self):
        config = load_config()

        self.assertFalse(config.safety.autonomy_enabled)

    def test_default_network_is_localhost(self):
        config = load_config()

        self.assertEqual(config.network.host, "127.0.0.1")
        self.assertTrue(config.network.authentication_required)

    def test_environment_override(self):
        with patch.dict(
            os.environ,
            {
                "RITHUM_NAME": "Rithum-Test",
                "RITHUM_LOG_LEVEL": "DEBUG",
                "RITHUM_WEB_PORT": "9000",
                "RITHUM_FACE_ENABLED": "false",
            },
        ):
            config = load_config()

        self.assertEqual(config.robot.name, "Rithum-Test")
        self.assertEqual(config.runtime.log_level, "DEBUG")
        self.assertEqual(config.network.port, 9000)
        self.assertFalse(config.runtime.face_enabled)

    def test_invalid_port_rejected(self):
        with patch.dict(
            os.environ,
            {"RITHUM_WEB_PORT": "70000"},
        ):
            with self.assertRaises(ValueError):
                load_config()

    def test_autonomy_requires_ir_sensors(self):
        with patch.dict(
            os.environ,
            {"RITHUM_AUTONOMY_ENABLED": "true"},
        ):
            with self.assertRaises(ValueError):
                load_config()

    def test_motors_cannot_be_enabled_at_boot(self):
        with patch.dict(
            os.environ,
            {"RITHUM_MOTORS_DISABLED_AT_BOOT": "false"},
        ):
            with self.assertRaises(ValueError):
                load_config()


if __name__ == "__main__":
    unittest.main(verbosity=2)
