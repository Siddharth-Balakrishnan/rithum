# Rithum Test Suite

## Install the test dependency

Activate the existing virtual environment, then install pytest:

```bash
source .venv/bin/activate
python -m pip install pytest
```

## Run the IPC tests only

```bash
pytest -v tests/test_ipc/
```

## Run the complete project test suite

```bash
pytest -v
```

The output is intentionally verbose: each test is listed separately. Pytest prints a
summary with passed, failed, and skipped counts. `pytest.ini` also enables concise
failure tracebacks and the short report for skipped/xfail tests.

## Test layout

```text
tests/
├── conftest.py
└── test_ipc/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_validator.py
    ├── test_framing.py
    ├── test_server.py
    └── test_client.py
```

The IPC tests use temporary Unix-domain sockets. They do not access GPIO, motors,
IR sensors, camera devices, or other physical hardware.

## Important

These tests are written against the IPC interfaces established during Rithum's
initial implementation. Run them on the Pi against the current source tree before
treating the suite as accepted. If an assertion fails because an implementation
signature differs, inspect the actual module and adapt the test to the implemented
contract rather than weakening the production code.
