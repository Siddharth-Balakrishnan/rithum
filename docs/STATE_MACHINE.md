# Operating State Machine

## 1. Purpose

`core/state_manager.py` owns the software representation of Rithum's operating state. It validates transitions and stores a bounded history. It does **not** control GPIO, disable a motor driver, or physically stop the rover. Those actions belong to the supervisor and hardware safety layer.

## 2. States

| State | Meaning |
|---|---|
| `BOOT` | Process/system startup state. |
| `SELF_TEST` | Startup or post-fault checks are being performed. |
| `IDLE` | Robot is available but not moving. |
| `MANUAL_LOCAL` | Local touchscreen/controller owns manual movement. |
| `MANUAL_REMOTE` | An authenticated remote client owns manual movement. |
| `AUTONOMOUS` | Later autonomous operating mode; disabled by default. |
| `HUMAN_INTERACTION` | Human-aware interaction mode; movement is expected to be disabled by supervisor policy. |
| `DIAGNOSTICS` | Diagnostic operation; motor outputs must remain disabled. |
| `SAFE_STOP` | Emergency-stop condition is latched. |
| `FAULT` | Critical hardware/software fault is latched. |

## 3. Normal transition graph

The current `TRANSITIONS` table in `core/state_manager.py` defines:

| Current state | Allowed normal next states |
|---|---|
| `BOOT` | `SELF_TEST` |
| `SELF_TEST` | `IDLE` |
| `IDLE` | `MANUAL_LOCAL`, `MANUAL_REMOTE`, `AUTONOMOUS`, `HUMAN_INTERACTION`, `DIAGNOSTICS` |
| `MANUAL_LOCAL` | `IDLE`, `HUMAN_INTERACTION` |
| `MANUAL_REMOTE` | `IDLE`, `HUMAN_INTERACTION` |
| `AUTONOMOUS` | `IDLE`, `HUMAN_INTERACTION` |
| `HUMAN_INTERACTION` | `IDLE` |
| `DIAGNOSTICS` | `IDLE` |
| `SAFE_STOP` | No normal transitions |
| `FAULT` | No normal transitions |

`SAFE_STOP`, `FAULT`, and `BOOT` cannot be entered using the ordinary `transition()` method. Safety/lifecycle methods own those transitions.

## 4. API reference

### Construction

```python
from core.state_manager import StateManager

manager = StateManager(
    autonomy_enabled=False,
    history_limit=1000,
)
```

- `autonomy_enabled` defaults to `False`.
- `history_limit` controls the maximum number of transition records retained.
- For the current rollout, autonomy must remain disabled until IR integration is complete.

### Read-only properties

```python
manager.state
manager.autonomy_enabled
manager.estop_latched
manager.fault_latched
manager.history
```

`state` returns an `OperatingState`. `history` returns an immutable tuple snapshot of `StateRecord` values.

### Normal transition

```python
from core.state_manager import OperatingState

manager.transition(
    OperatingState.SELF_TEST,
    reason="Boot sequence started",
)
```

`reason` is keyword-only and must be non-empty. The target must be an `OperatingState` and must be legal from the current state.

### Emergency stop

```python
manager.emergency_stop(reason="Physical emergency stop activated")
```

- Sets the E-stop latch.
- Moves to `SAFE_STOP`, unless already in `FAULT`.
- Does not physically disable outputs. The supervisor must do that independently.

### Fault report

```python
manager.report_fault(reason="Motor driver communication lost")
```

- Sets the fault latch.
- Moves to `FAULT`.
- Does not itself diagnose or clear the physical/software fault.

### Confirm physical E-stop release

```python
manager.confirm_estop_released(
    hardware_confirmed_released=True,
)
```

The caller must have independently verified that the physical E-stop is released. Passing `False` raises `StateTransitionError`.

This clears the latch only; it does not leave `SAFE_STOP`.

### Recover from safe stop

```python
manager.reset_safe_stop(safety_checks_passed=True)
```

Requires current state `SAFE_STOP`, E-stop latch cleared, and safety checks passed. Successful recovery moves to `IDLE`.

### Recover from fault

```python
manager.recover_fault(
    fault_condition_cleared=True,
    safety_checks_passed=True,
)
```

Requires current state `FAULT`, E-stop latch cleared, fault condition cleared, and safety checks passed. Successful recovery clears the fault latch and moves to `SELF_TEST`. A fresh self-test must pass before returning to `IDLE`.

## 5. Exceptions and their meaning

- `TypeError`: target is not an `OperatingState`.
- `ValueError`: a required reason is empty/blank.
- `StateTransitionError`: requested transition is illegal, safety latch remains active, recovery conditions are unmet, or autonomy is disabled.

Do not catch `StateTransitionError` and continue as if the requested mode was entered. A rejected transition means the requested operation did not happen.

## 6. History records

Each `StateRecord` contains:

- `timestamp`: UTC ISO-8601 timestamp;
- `previous`: prior `OperatingState`;
- `current`: resulting `OperatingState`;
- `reason`: human-readable transition reason.

History is bounded by `history_limit`. It is in-memory and is not a durable audit log. A process restart loses this history unless a future persistence layer is added.

## 7. Important invariants

1. `SAFE_STOP` cannot be exited through `transition()`.
2. `FAULT` cannot be exited through `transition()`.
3. E-stop must be physically confirmed released before safe-stop recovery.
4. Fault recovery requires the fault condition to be cleared and safety checks to pass.
5. Fault recovery returns to `SELF_TEST`, not directly to `IDLE`.
6. Autonomous transition is rejected unless the manager was constructed with `autonomy_enabled=True`.
7. Even if autonomy is enabled in configuration, supervisor policy must still verify IR hardware readiness and phase completion.
8. The state manager is not the motor safety circuit.

## 8. Known design considerations for future review

- `autonomy_enabled` is constructor-level and has no runtime setter in the current class.
- The state manager trusts its caller's `hardware_confirmed_released`, `fault_condition_cleared`, and `safety_checks_passed` booleans. The future supervisor must be the trusted source of these confirmations.
- `confirm_estop_released()` clears the E-stop latch but does not create a history record.
- `report_fault()` can move the state to `FAULT` from any state. `emergency_stop()` deliberately does not downgrade an existing `FAULT`.
- Face/display state is not represented here and should remain separate.

## 9. Debugging a rejected transition

1. Print `manager.state`.
2. Confirm the exact target enum.
3. Check the transition table above.
4. Check `manager.estop_latched` and `manager.fault_latched`.
5. Check whether autonomy is enabled.
6. Inspect the exception text.
7. Add a test for the intended behavior before changing the transition table.

Never weaken safety transitions just to make a test pass.
