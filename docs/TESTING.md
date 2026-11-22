# Testing Guide

## 1. Test philosophy

Rithum's unit tests should be deterministic and should not require motors, GPIO, a camera, an IR sensor, a network tunnel, or the touchscreen to be attached.

Hardware-in-the-loop tests are a separate category and must have explicit safety setup and instructions.

## 2. Run all tests

From the repository root with the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

The recorded initial baseline:

```text
Ran 23 tests
OK
```

Breakdown:
- 9 configuration tests;
- 14 state-manager tests.

This count is a historical baseline. If tests are added or removed, update this document and the README.

## 3. Run an individual test module

The most portable command is discovery with a pattern:

```bash
python -m unittest discover -s tests -p 'test_config.py' -v
python -m unittest discover -s tests -p 'test_state_manager.py' -v
```

## 4. Configuration test coverage

The existing configuration tests cover:
- default configuration;
- motor integration disabled by default;
- IR integration disabled by default;
- autonomy disabled by default;
- localhost binding and authentication default;
- environment-variable override;
- invalid web port rejection;
- autonomy requiring IR sensors;
- motor outputs required to remain disabled at boot.

When adding a configuration field, test its default, environment parsing, invalid input, and any cross-field validation.

## 5. State-manager test coverage

The existing state-manager tests cover:
- initial `BOOT` state;
- `BOOT` to `SELF_TEST` to `IDLE`;
- invalid transition rejection;
- local and remote manual modes;
- autonomy disabled by default;
- explicit autonomy enablement;
- emergency-stop latching;
- no bypass of `SAFE_STOP`;
- E-stop release requirement;
- safe-stop recovery;
- fault recovery blocked until condition cleared;
- fault recovery returning to `SELF_TEST`;
- transition history recording.

When changing the state graph, update both the transition documentation and tests.

## 6. Test design rules

- Assert the resulting state, not only that no exception occurred.
- Assert rejected operations leave state unchanged.
- Test both positive and negative paths.
- Test missing/blank reasons.
- Test safety latches and recovery prerequisites independently.
- Test history contents and bounds.
- Test autonomy-disabled behavior explicitly.
- Do not weaken safety logic to satisfy a test.
- Avoid timing-sensitive sleeps; use fake clocks or injected timing abstractions for future heartbeat tests.

## 7. Debugging a failing test

1. Re-run only the failing module.
2. Read the first traceback, not just the final summary.
3. Identify whether the failure is an API mismatch, incorrect expectation, implementation bug, or environment issue.
4. Inspect the actual source signature before changing a test.
5. Reproduce with the smallest test.
6. Fix the cause and rerun the focused test.
7. Run the complete suite before committing.

Useful commands:

```bash
python -m unittest discover -s tests -p 'test_state_manager.py' -v
python -m unittest discover -s tests -p 'test_config.py' -v
python -m unittest discover -s tests -v
```

## 8. Hardware test boundary

Do not run hardware tests with the robot resting on the floor unless the test explicitly requires it and the area is clear. For first motor tests:
- raise the wheels;
- use low duty cycle;
- test one channel at a time;
- verify E-stop;
- verify stop-on-disconnect/timeout;
- keep a person ready to disconnect motor power.

A passing unit test does not validate wiring, motor polarity, current capacity, sensor range, or physical stopping distance.
