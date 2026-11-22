# Development Guide

## 1. Development host

The primary target is a Raspberry Pi 5 running 64-bit Ubuntu. The recorded setup used:

- Ubuntu 26.10 ARM64;
- Python 3.14.8;
- Git;
- a project-local `.venv`;
- `gpiod` Python bindings 2.6.0 using the libgpiod v2 API.

These versions may change. Record actual versions when reproducing an issue.

## 2. Clone the repository

```bash
git clone git@github.com:Siddharth-Balakrishnan/rithum.git
cd rithum
```

If SSH is not configured, use the repository's HTTPS clone URL instead. Do not place a personal access token in the remote URL.

## 3. Create/activate the virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Confirm interpreter and pip:

```bash
which python
python --version
python -m pip --version
```

The `which python` path should point inside the repository's `.venv`.

## 4. Install dependencies

Inspect `requirements.txt` before installing:

```bash
cat requirements.txt
python -m pip install -r requirements.txt
```

Do not add packages because they might be useful later. Add a dependency only when a concrete implementation requires it, and pin or constrain versions deliberately.

For hardware libraries, distinguish:
- system packages installed through APT;
- Python packages installed in `.venv`;
- kernel drivers/modules;
- hardware device permissions.

A Python package cannot replace a missing kernel driver or electrically incompatible sensor.

## 5. Useful system packages

The initial system setup installed or confirmed these packages:

```text
git
curl
sqlite3
libsqlite3-dev
python3-dev
build-essential
pkg-config
libgpiod-dev
v4l-utils
usbutils
evtest
```

This is a setup record, not a complete dependency manifest. Confirm package availability for the target Ubuntu release before installing.

## 6. Run the project foundation

```bash
python -m core.config
python -m unittest discover -s tests -v
```

Do not start unimplemented services by guessing module names.

## 7. Code organization rules

- Keep hardware access inside `hardware/`.
- Keep wheel kinematics and motion command logic inside `motion/`.
- Keep state transitions in `core/state_manager.py`.
- Keep configuration parsing/validation in `core/config.py`.
- Keep web routes and UI assets under `web/`.
- Keep camera/vision code under `vision/`.
- Keep face rendering under `face/`.
- Keep Alexa/voice integration under `voice/`.
- Keep diagnostics read-only unless a test explicitly requests a controlled hardware action.
- Add tests alongside every new behavior.
- Avoid circular imports between core, hardware, motion, and web layers.

## 8. Error handling and logging

Errors should contain enough context to debug:
- subsystem;
- operation;
- state/mode;
- relevant device identifier;
- exception class and message;
- whether outputs were disabled;
- correlation/request ID for API-driven actions.

Do not log passwords, tokens, private keys, session cookies, or complete environment dumps.

## 9. Hardware-independent tests

Prefer dependency injection and fake hardware interfaces. A unit test should be able to test:
- motor mixing without a motor driver connected;
- state transitions without GPIO;
- sensor interpretation from supplied values;
- API validation without a physical rover;
- heartbeat expiry using a controlled clock/fake scheduler.

Physical hardware tests should be clearly marked and must begin with a safe setup.

## 10. Git workflow

```bash
git status --short
git diff
git add <specific-files>
git diff --cached
git commit -m "type: concise description"
git push
```

Use focused commits. Do not commit `.venv/`, logs, local databases, credentials, private SSH keys, or generated runtime data.

## 11. Before opening a pull request

- Run the complete test suite.
- Review the staged diff.
- Update relevant docs.
- Add tests for behavior changes.
- Confirm no credentials or private data are included.
- Confirm safety invariants remain true.
- State clearly whether the change is implemented, experimental, or a design-only addition.
