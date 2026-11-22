
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import RLock


class OperatingState(str, Enum):
    BOOT = "BOOT"
    SELF_TEST = "SELF_TEST"
    IDLE = "IDLE"

    MANUAL_LOCAL = "MANUAL_LOCAL"
    MANUAL_REMOTE = "MANUAL_REMOTE"
    AUTONOMOUS = "AUTONOMOUS"

    HUMAN_INTERACTION = "HUMAN_INTERACTION"
    DIAGNOSTICS = "DIAGNOSTICS"

    SAFE_STOP = "SAFE_STOP"
    FAULT = "FAULT"


class StateTransitionError(RuntimeError):
    """Raised when an operating-state transition is invalid."""


@dataclass(frozen=True)
class StateRecord:
    timestamp: str
    previous: OperatingState
    current: OperatingState
    reason: str


class StateManager:
    """
    Maintains Rithum's operating state.

    This class does not control motors or GPIO.
    The supervisor is responsible for enforcing hardware actions.
    """

    # Normal transitions only. SAFE_STOP and FAULT are handled
    # through dedicated safety methods.
    TRANSITIONS = {
        OperatingState.BOOT: {
            OperatingState.SELF_TEST,
        },
        OperatingState.SELF_TEST: {
            OperatingState.IDLE,
        },
        OperatingState.IDLE: {
            OperatingState.MANUAL_LOCAL,
            OperatingState.MANUAL_REMOTE,
            OperatingState.AUTONOMOUS,
            OperatingState.HUMAN_INTERACTION,
            OperatingState.DIAGNOSTICS,
        },
        OperatingState.MANUAL_LOCAL: {
            OperatingState.IDLE,
            OperatingState.HUMAN_INTERACTION,
        },
        OperatingState.MANUAL_REMOTE: {
            OperatingState.IDLE,
            OperatingState.HUMAN_INTERACTION,
        },
        OperatingState.AUTONOMOUS: {
            OperatingState.IDLE,
            OperatingState.HUMAN_INTERACTION,
        },
        OperatingState.HUMAN_INTERACTION: {
            OperatingState.IDLE,
        },
        OperatingState.DIAGNOSTICS: {
            OperatingState.IDLE,
        },
        OperatingState.SAFE_STOP: set(),
        OperatingState.FAULT: set(),
    }

    def __init__(
        self,
        *,
        autonomy_enabled: bool = False,
        history_limit: int = 1000,
    ) -> None:
        self._state = OperatingState.BOOT
        self._autonomy_enabled = autonomy_enabled

        self._estop_latched = False
        self._fault_latched = False

        self._history: deque[StateRecord] = deque(
            maxlen=history_limit
        )

        self._lock = RLock()

    @property
    def state(self) -> OperatingState:
        with self._lock:
            return self._state

    @property
    def autonomy_enabled(self) -> bool:
        return self._autonomy_enabled

    @property
    def estop_latched(self) -> bool:
        with self._lock:
            return self._estop_latched

    @property
    def fault_latched(self) -> bool:
        with self._lock:
            return self._fault_latched

    @property
    def history(self) -> tuple[StateRecord, ...]:
        with self._lock:
            return tuple(self._history)

    def _record(
        self,
        previous: OperatingState,
        current: OperatingState,
        reason: str,
    ) -> None:
        self._history.append(
            StateRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                previous=previous,
                current=current,
                reason=reason,
            )
        )

    def _set_state(
        self,
        target: OperatingState,
        reason: str,
    ) -> None:
        previous = self._state
        self._state = target
        self._record(previous, target, reason)

    def transition(
        self,
        target: OperatingState,
        *,
        reason: str,
    ) -> None:
        """Perform a validated normal state transition."""

        if not isinstance(target, OperatingState):
            raise TypeError("target must be an OperatingState")

        if not reason or not reason.strip():
            raise ValueError("A transition reason is required")

        with self._lock:
            if self._state in {
                OperatingState.SAFE_STOP,
                OperatingState.FAULT,
            }:
                raise StateTransitionError(
                    f"Cannot transition out of {self._state.value} "
                    "without explicit recovery"
                )

            if target in {
                OperatingState.SAFE_STOP,
                OperatingState.FAULT,
                OperatingState.BOOT,
            }:
                raise StateTransitionError(
                    f"{target.value} requires a dedicated safety "
                    "or lifecycle method"
                )

            if (
                target == OperatingState.AUTONOMOUS
                and not self._autonomy_enabled
            ):
                raise StateTransitionError(
                    "Autonomous mode is disabled until IR "
                    "integration is completed"
                )

            allowed = self.TRANSITIONS[self._state]

            if target not in allowed:
                raise StateTransitionError(
                    f"Invalid transition: {self._state.value} "
                    f"-> {target.value}"
                )

            self._set_state(target, reason.strip())

    def emergency_stop(self, *, reason: str) -> None:
        """
        Latch an emergency stop.

        This records the stop condition. The supervisor must
        independently disable motor outputs immediately.
        """

        if not reason or not reason.strip():
            raise ValueError("An emergency-stop reason is required")

        with self._lock:
            self._estop_latched = True

            # Never downgrade an existing hardware fault.
            if self._state != OperatingState.FAULT:
                if self._state != OperatingState.SAFE_STOP:
                    self._set_state(
                        OperatingState.SAFE_STOP,
                        reason.strip(),
                    )

    def report_fault(self, *, reason: str) -> None:
        """Latch a hardware or critical software fault."""

        if not reason or not reason.strip():
            raise ValueError("A fault reason is required")

        with self._lock:
            self._fault_latched = True

            if self._state != OperatingState.FAULT:
                self._set_state(
                    OperatingState.FAULT,
                    reason.strip(),
                )

    def confirm_estop_released(
        self,
        *,
        hardware_confirmed_released: bool,
    ) -> None:
        """
        Clear the E-stop latch only after the supervisor has
        verified that the physical E-stop is released.
        """

        if not hardware_confirmed_released:
            raise StateTransitionError(
                "Physical emergency stop is still active"
            )

        with self._lock:
            self._estop_latched = False

    def reset_safe_stop(
        self,
        *,
        safety_checks_passed: bool,
    ) -> None:
        """Recover from SAFE_STOP after safety confirmation."""

        with self._lock:
            if self._state != OperatingState.SAFE_STOP:
                raise StateTransitionError(
                    "Robot is not in SAFE_STOP"
                )

            if self._estop_latched:
                raise StateTransitionError(
                    "Emergency-stop latch is still active"
                )

            if not safety_checks_passed:
                raise StateTransitionError(
                    "Safety checks have not passed"
                )

            self._set_state(
                OperatingState.IDLE,
                "Safe-stop recovery approved",
            )

    def recover_fault(
        self,
        *,
        fault_condition_cleared: bool,
        safety_checks_passed: bool,
    ) -> None:
        """
        Recover from FAULT into SELF_TEST.

        A fresh self-test is mandatory before returning to IDLE.
        """

        with self._lock:
            if self._state != OperatingState.FAULT:
                raise StateTransitionError(
                    "Robot is not in FAULT"
                )

            if self._estop_latched:
                raise StateTransitionError(
                    "Emergency-stop latch is still active"
                )

            if not fault_condition_cleared:
                raise StateTransitionError(
                    "Fault condition has not been cleared"
                )

            if not safety_checks_passed:
                raise StateTransitionError(
                    "Safety checks have not passed"
                )

            self._fault_latched = False
            self._set_state(
                OperatingState.SELF_TEST,
                "Fault recovery approved; self-test required",
            )
