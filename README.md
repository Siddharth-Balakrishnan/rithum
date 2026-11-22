# Rithum

**Rithum** (also referred to as `r1t-hum` or `rit-hum`) is a Raspberry Pi 5-based four-wheel mecanum rover. The project is being developed as a single-board-computer robot with local and remote manual control first, followed by sensor-assisted obstacle avoidance and autonomous operation in a later phase.

Repository: <https://github.com/Siddharth-Balakrishnan/rithum>

> **Project status:** early software foundation. Configuration loading, operating-state management, and their unit tests are present. The motion, sensor, vision, face, voice, web-control, and supervisor subsystems described in the architecture are design targets unless a source file implementing them has subsequently been added. Do not assume a feature is operational just because it appears in this documentation.

## Contents

- [1. Project goals](#1-project-goals)
- [2. Current implementation status](#2-current-implementation-status)
- [3. Hardware at a glance](#3-hardware-at-a-glance)
- [4. Software architecture](#4-software-architecture)
- [5. Repository layout](#5-repository-layout)
- [6. Documentation index](#6-documentation-index)
- [7. Development environment](#7-development-environment)
- [8. Quick start](#8-quick-start)
- [9. Tests](#9-tests)
- [10. Safety rules](#10-safety-rules)
- [11. Debugging entry points](#11-debugging-entry-points)
- [12. Project principles](#12-project-principles)

## 1. Project goals

Rithum is intended to provide:

1. Four-wheel mecanum movement: forward, reverse, lateral, diagonal, and rotation.
2. Manual control from a PC browser, a mobile browser, and the robot's local touchscreen.
3. A local animated robot face, with a local touchscreen mode that can switch to the control interface.
4. Human-presence and face-related interaction using a camera, introduced after the basic control path is stable.
5. Alexa-assisted voice interaction, with robot-specific commands routed through an integration service.
6. Four-direction obstacle sensing using IR sensors.
7. A later autonomous mode, enabled only after the manual-control foundation and IR integration have been tested.

The rollout is deliberately staged. The initial movement implementation is **UI-controlled only**. IR-based autonomous movement must not be enabled before the designated autonomy phase is complete.

## 2. Current implementation status

The following reflects the repository state established during the initial software setup. Re-check the tree and tests before relying on this table after future changes.

| Area | Status | Notes |
|---|---|---|
| Python project and virtual environment | Present | Python 3.14.8 was observed on the Raspberry Pi during setup. |
| Configuration model | Implemented | `core/config.py`; environment-variable configuration and validation. |
| Operating-state manager | Implemented | `core/state_manager.py`; validates state transitions and records history. |
| Configuration tests | Implemented | `tests/test_config.py`. |
| State-manager tests | Implemented | `tests/test_state_manager.py`. |
| Supervisor/process lifecycle | Planned | Not part of the current verified implementation. |
| Motor driver/GPIO integration | Planned | Motor outputs must remain disabled until the hardware layer is implemented and tested. |
| Web controller and WebSocket API | Planned | PC, mobile, and local UI are design targets. |
| IR obstacle sensing | Planned | Four sensors are intended; exact sensor model and wiring must be documented when selected. |
| Autonomous navigation | Deferred | Must remain disabled until the IR integration phase is completed and validated. |
| Camera/vision and human detection | Planned | No camera was detected in the recorded initial hardware inventory. |
| Face renderer | Planned | Intended to use a lightweight native display stack, not a browser/Electron kiosk. |
| Alexa integration | Planned | General Alexa interaction and robot-specific commands have different integration paths. |
| systemd deployment | Planned | No production service unit should be assumed to exist yet. |

The test baseline recorded after the state-manager test correction was:

```text
Ran 23 tests
OK
```

This is a historical baseline, not a guarantee that the current checkout still passes. Run the test command in [TESTING.md](docs/TESTING.md).

## 3. Hardware at a glance

The current bill of materials includes:

| Component | Model / specification | Quantity | Intended role |
|---|---|---:|---|
| Single-board computer | Raspberry Pi 5, 8 GB | 1 | Main computer and control host |
| DC geared motor | OG555, 12 V, 100 RPM | 4 | Wheel drive |
| Motor driver | Cytron MDD10A, dual channel | 2 | Two motor channels per driver |
| Mecanum wheels | 100 mm, 2 left + 2 right | 1 set | Omnidirectional movement |
| Encoders | OE-37, two-channel Hall effect | 2 | Optional testing/feedback |
| Main battery | 14.8 V nominal, 10 Ah, 4S Li-ion | 1 | Main robot power |
| Charger | 16.8 V, 5 A, 4S Li-ion | 1 | Battery charging |
| Voice assistant | Echo Dot 5th generation | 1 | Alexa voice interface |
| Touchscreen | 7-inch, listed as 1200 × 700 | 1 | Local face/control display |
| IR obstacle sensors | Four units, model TBD | 4 | Later obstacle detection/avoidance |
| Camera | USB webcam, target budget ≤ ₹1,500 | 1 | Later vision/human detection |
| Pi power source | Regulated USB-C supply/power bank | 1 | Pi power; display power budget must be considered separately |

**Hardware data caveats:** the supplied BOM contains a battery configuration inconsistency: the product heading/link refers to 4S4P in one place while the detailed specification says 4S3P. Confirm the actual battery label and manufacturer data before calculating safe discharge current. The actual touchscreen model is not yet identified. Confirm its native resolution, touch interface, and power requirements before finalizing display setup.

See [HARDWARE.md](docs/HARDWARE.md) for integration notes and unresolved items.

## 4. Software architecture

The intended design is a single Raspberry Pi host running native Linux processes. It does not require Docker or an additional microcontroller.

High-level target:

```text
PC browser ─────┐
Mobile browser ─┼── LAN / Tailscale / protected remote access
Local touch UI ─┘                 │
                                 ▼
                         Web/API service
                                 │
                          authenticated IPC
                                 │
                                 ▼
                       Python supervisor
                                 │
               ┌─────────────────┼─────────────────┐
               ▼                 ▼                 ▼
          State manager     Safety manager     Process manager
               │                 │                 │
               └─────────────────┼─────────────────┘
                                 │
        ┌──────────────┬─────────┼──────────┬──────────────┐
        ▼              ▼         ▼          ▼              ▼
     Motion          Vision     Face       Voice        Diagnostics
        │              │        renderer    /Alexa
        ▼              ▼
   Motor drivers    Camera / IR sensors (IR later)
```

This is a target architecture, not a diagram of currently running services. The supervisor is intended to be the authority for operating modes, worker lifecycle, and safety interlocks. Web clients must never be given direct GPIO or raw motor-driver access.

More detail: [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. Repository layout

The expected project layout is:

```text
rithum/
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── state_manager.py
├── hardware/
├── motion/
├── vision/
├── face/
│   └── assets/
│       ├── eyes/
│       ├── mouths/
│       └── expressions/
├── voice/
├── web/
│   ├── routes/
│   └── static/
│       ├── css/
│       ├── js/
│       └── assets/
├── diagnostics/
├── storage/
│   ├── data/
│   └── logs/
├── config/
├── scripts/
├── tests/
│   ├── test_config.py
│   └── test_state_manager.py
├── docs/
├── .gitignore
├── README.md
├── requirements.txt
└── .venv/                 # local only; ignored by Git
```

Some directories are scaffolding for future subsystems and may be empty. An empty directory is not proof that its feature is implemented.

## 6. Documentation index

| File | Purpose | Read it when… |
|---|---|---|
| [`README.md`](README.md) | Project landing page, current status, setup entry points, and documentation index. | You are new to the repository. |
| [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | Goals, scope, operating principles, terminology, and implementation boundaries. | You need to understand what Rithum is supposed to do. |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Target subsystem architecture, process boundaries, IPC, ownership, and request flow. | You are adding a subsystem or tracing cross-module behavior. |
| [`docs/STATE_MACHINE.md`](docs/STATE_MACHINE.md) | Operating states, legal transitions, latches, recovery paths, and state-manager API. | A mode change is rejected or the robot enters a stop/fault state. |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Configuration sections, environment variables, defaults, validation, and safe configuration practice. | A setting is wrong or startup validation fails. |
| [`docs/HARDWARE.md`](docs/HARDWARE.md) | BOM, subsystem allocation, electrical integration constraints, and hardware items still to verify. | You are wiring, replacing, or diagnosing hardware. |
| [`docs/SAFETY.md`](docs/SAFETY.md) | Motor-output safety, emergency stop, power separation, remote-control safety, and autonomy gates. | You are changing anything that can move the rover or energize hardware. |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | Repository workflow, virtual environment, dependencies, code conventions, and change procedure. | You are setting up a development environment or contributing code. |
| [`docs/TESTING.md`](docs/TESTING.md) | Test commands, test scope, expected baseline, and how to interpret failures. | You changed code or need to verify a checkout. |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Symptom-led debugging checklist and useful Linux/Python commands. | Something fails and you need a repeatable diagnosis. |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase gates, implementation sequence, deferred autonomy, and completion criteria. | You need to decide what should be built next. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Branch, commit, review, documentation, and safety requirements for changes. | You are preparing a change for the repository. |
| [`SECURITY.md`](SECURITY.md) | Credential handling, network exposure, authentication, and vulnerability reporting expectations. | You are configuring remote access or handling secrets. |

Keep this index synchronized whenever Markdown files are added, removed, or renamed.

## 7. Development environment

Recorded Raspberry Pi baseline during initial setup:

- Board: Raspberry Pi 5 Model B, 8 GB.
- OS: Ubuntu 26.10, 64-bit ARM (`aarch64`).
- Kernel: `7.3.0-1004-raspi`.
- Python: `3.14.8`.
- Virtual environment: `.venv/`.
- GPIO library/API: `gpiod` 2.6.0 / libgpiod v2 API was verified.
- Graphics devices and `vc4`/`v3d` kernel modules were present.
- No USB webcam or touchscreen was detected in the recorded inventory.
- Network interfaces included Wi-Fi and Tailscale.

These are time-specific observations. Use `uname -a`, `python --version`, `gpiodetect`, `lsusb`, and `ip -br address` to inspect the current machine.

## 8. Quick start

From the repository root:

```bash
cd ~/projects/rithum

# Activate the existing virtual environment.
source .venv/bin/activate

# Inspect the project and current Git state.
git status --short --branch

# Print the validated application configuration.
python -m core.config

# Run all unit tests.
python -m unittest discover -s tests -v
```

If the virtual environment does not exist:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Install project dependencies only after checking the current `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

Do not install guessed dependencies or run the application as root unless a specific hardware permission requirement has been established. The current development session has been using the root account, but a dedicated unprivileged service/development account is preferable before deployment.

## 9. Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The verified initial baseline is 23 tests: 9 configuration tests and 14 state-manager tests. Tests should remain hardware-independent wherever possible. Unit tests must not energize motors, access real GPIO, or require the camera.

See [TESTING.md](docs/TESTING.md).

## 10. Safety rules

- Motor outputs must be disabled at boot.
- Software state changes alone do not physically stop motors. The supervisor and hardware layer must enforce output disable.
- A physical emergency-stop mechanism must interrupt motor power independently of the Pi software.
- Never connect a 12 V signal or motor supply directly to a Raspberry Pi GPIO.
- Verify the electrical output type of every sensor before connecting it to 3.3 V GPIO.
- Do not expose raw motor-control endpoints to the Internet.
- Remote control must use authentication, one active operator lease, heartbeat/dead-man behavior, and stop-on-disconnect.
- Autonomy remains disabled until the IR integration phase is complete and validated.
- Encoders are optional test instrumentation; they are not required to be continuously connected in the initial manual-control phase.

Read [SAFETY.md](docs/SAFETY.md) before changing hardware or motion code.

## 11. Debugging entry points

Start with the narrowest relevant layer:

1. **Configuration/startup:** run `python -m core.config`; inspect environment variables and validation errors.
2. **State transitions:** inspect `core/state_manager.py`, then run `python -m unittest tests.test_state_manager -v` if package-style test invocation is supported; otherwise use discovery.
3. **Regression:** run the complete test suite.
4. **Hardware enumeration:** use `lsusb`, `v4l2-ctl --list-devices`, `gpiodetect`, `gpioinfo`, and `ls -l /dev/dri/`.
5. **Linux services:** use `systemctl --failed`, `systemctl status <unit>`, and `journalctl -u <unit> -b`.
6. **Network:** use `ip -br address`, `ip route`, `tailscale status`, and local socket inspection.
7. **Git:** use `git status`, `git diff`, and `git log --oneline --decorate -10`.

Do not begin by changing multiple subsystems at once. Reproduce the issue, capture the relevant output, isolate the layer, make one change, and rerun the relevant tests.

## 12. Project principles

- One Raspberry Pi is the primary compute and control platform.
- Native Linux processes and `systemd` are preferred; Docker is not part of the current design.
- No additional microcontroller is planned.
- Python is the primary backend/control language.
- FastAPI and a lightweight browser interface are the planned web-control approach; do not treat them as installed or implemented until the code exists.
- Local and remote control must share the same validated command path.
- The supervisor, not the browser, owns operating-mode decisions.
- Safety behavior must fail closed: uncertain state means motors disabled.
- Build and verify manual control before introducing autonomy.
- Documentation must distinguish verified implementation from planned design.
