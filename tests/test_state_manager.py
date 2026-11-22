import unittest

from core.state_manager import (
    OperatingState,
    StateManager,
    StateTransitionError,
)


class TestStateManager(unittest.TestCase):

    def setUp(self):
        self.manager = StateManager()

    def boot_to_idle(self):
        self.manager.transition(
            OperatingState.SELF_TEST,
            reason="Boot sequence started",
        )
        self.manager.transition(
            OperatingState.IDLE,
            reason="Self-test passed",
        )

    def test_initial_state(self):
        self.assertEqual(
            self.manager.state,
            OperatingState.BOOT,
        )

    def test_boot_to_idle(self):
        self.boot_to_idle()

        self.assertEqual(
            self.manager.state,
            OperatingState.IDLE,
        )

    def test_invalid_transition(self):
        with self.assertRaises(StateTransitionError):
            self.manager.transition(
                OperatingState.MANUAL_LOCAL,
                reason="Invalid boot transition",
            )

    def test_manual_local(self):
        self.boot_to_idle()

        self.manager.transition(
            OperatingState.MANUAL_LOCAL,
            reason="Local controller activated",
        )

        self.assertEqual(
            self.manager.state,
            OperatingState.MANUAL_LOCAL,
        )

    def test_manual_remote(self):
        self.boot_to_idle()

        self.manager.transition(
            OperatingState.MANUAL_REMOTE,
            reason="Remote controller activated",
        )

        self.assertEqual(
            self.manager.state,
            OperatingState.MANUAL_REMOTE,
        )

    def test_autonomy_disabled_by_default(self):
        self.assertFalse(self.manager.autonomy_enabled)

        self.boot_to_idle()

        with self.assertRaises(StateTransitionError):
            self.manager.transition(
                OperatingState.AUTONOMOUS,
                reason="Attempt autonomous mode",
            )

    def test_autonomy_requires_explicit_enablement(self):
        autonomous_manager = StateManager(
            autonomy_enabled=True,
        )

        autonomous_manager.transition(
            OperatingState.SELF_TEST,
            reason="Boot sequence started",
        )
        autonomous_manager.transition(
            OperatingState.IDLE,
            reason="Self-test passed",
        )
        autonomous_manager.transition(
            OperatingState.AUTONOMOUS,
            reason="Autonomous mode activated",
        )

        self.assertEqual(
            autonomous_manager.state,
            OperatingState.AUTONOMOUS,
        )

    def test_emergency_stop_latches(self):
        self.boot_to_idle()

        self.manager.emergency_stop(
            reason="Emergency stop button pressed",
        )

        self.assertEqual(
            self.manager.state,
            OperatingState.SAFE_STOP,
        )
        self.assertTrue(self.manager.estop_latched)

    def test_safe_stop_cannot_be_bypassed(self):
        self.boot_to_idle()

        self.manager.emergency_stop(
            reason="Emergency stop activated",
        )

        with self.assertRaises(StateTransitionError):
            self.manager.transition(
                OperatingState.IDLE,
                reason="Attempt to bypass safe stop",
            )

        self.assertEqual(
            self.manager.state,
            OperatingState.SAFE_STOP,
        )

    def test_safe_stop_requires_estop_release(self):
        self.boot_to_idle()

        self.manager.emergency_stop(
            reason="Emergency stop activated",
        )

        with self.assertRaises(StateTransitionError):
            self.manager.reset_safe_stop(
                safety_checks_passed=True,
            )

        self.assertEqual(
            self.manager.state,
            OperatingState.SAFE_STOP,
        )

    def test_safe_stop_recovery(self):
        self.boot_to_idle()

        self.manager.emergency_stop(
            reason="Emergency stop activated",
        )

        self.manager.confirm_estop_released(
            hardware_confirmed_released=True,
        )

        self.manager.reset_safe_stop(
            safety_checks_passed=True,
        )

        self.assertFalse(self.manager.estop_latched)
        self.assertEqual(
            self.manager.state,
            OperatingState.IDLE,
        )

    def test_fault_cannot_recover_without_clear_condition(self):
        self.boot_to_idle()

        self.manager.report_fault(
            reason="Motor driver fault",
        )

        with self.assertRaises(StateTransitionError):
            self.manager.recover_fault(
                fault_condition_cleared=False,
                safety_checks_passed=True,
            )

        self.assertEqual(
            self.manager.state,
            OperatingState.FAULT,
        )
        self.assertTrue(self.manager.fault_latched)

    def test_fault_recovery_requires_self_test(self):
        self.boot_to_idle()

        self.manager.report_fault(
            reason="Critical hardware fault",
        )

        self.manager.recover_fault(
            fault_condition_cleared=True,
            safety_checks_passed=True,
        )

        self.assertFalse(self.manager.fault_latched)
        self.assertEqual(
            self.manager.state,
            OperatingState.SELF_TEST,
        )

        self.manager.transition(
            OperatingState.IDLE,
            reason="Post-recovery self-test passed",
        )

        self.assertEqual(
            self.manager.state,
            OperatingState.IDLE,
        )

    def test_history_records_transitions(self):
        self.boot_to_idle()

        history = self.manager.history

        self.assertEqual(len(history), 2)
        self.assertEqual(
            history[0].previous,
            OperatingState.BOOT,
        )
        self.assertEqual(
            history[0].current,
            OperatingState.SELF_TEST,
        )
        self.assertEqual(
            history[1].previous,
            OperatingState.SELF_TEST,
        )
        self.assertEqual(
            history[1].current,
            OperatingState.IDLE,
        )
        self.assertTrue(history[0].timestamp)
        self.assertEqual(
            history[0].reason,
            "Boot sequence started",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
