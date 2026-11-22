# Rithum

Rithum is a Raspberry Pi 5-based mecanum rover project. Its software is designed around a central Python supervisor, independently managed worker processes, a safety-oriented operating-state manager, and a responsive control interface.

The project is being developed incrementally. Features documented as planned or reserved are not necessarily implemented.

## Project goals

- Provide responsive manual control from a PC, mobile device, and the rover's local touchscreen.
- Use a dedicated face renderer for expressions and visual feedback.
- Add vision-based human detection and interaction.
- Integrate voice/ Alexa-related commands through a controlled bridge.
- Introduce IR-based obstacle detection and autonomous movement only after the manual-control milestone is complete.
- Keep hardware access and operating-state authority centralized.
- Keep the system lightweight and native to Ubuntu on Raspberry Pi.

## Hardware and platform

Current target platform:

- Raspberry Pi 5 Model B, 8 GB RAM.
- Ubuntu Server 26.10, ARM64.
- Mecanum drive base with four motor channels.
- Main battery and regulated power distribution for the rover electronics.
- HDMI display during early development; intended 7-inch touchscreen later.
- Camera for vision features.
- Four IR obstacle sensors planned for the later autonomy phase.

Hardware interfaces and pin assignments must be confirmed against the actual components before enabling outputs. Motors remain disabled by default during software development.

## Architecture overview

Rithum uses a single-board-computer architecture with native Linux processes. It does not require Docker or an additional microcontroller for the planned software architecture.

```text
                   PC / Mobile / Local UI
                            |
                      Web Controller
                            |
                    Authenticated API
                            |
                     Core Supervisor
                    /    |     |     \
                   /     |     |      \
             Motion   Face   Vision   Voice
             Worker  Renderer Worker  Bridge
                |       |       |       |
           Hardware  Display  Camera  Alexa /
            Layer                      Voice Events
                   |
              Diagnostics
```

The supervisor is responsible for process lifecycle, message validation, operating-state coordination, and safety policy. Workers perform their assigned tasks but do not independently grant themselves authority or control sibling processes.

### Core principles

- The supervisor is the central process and state authority.
- Hardware access is mediated through controlled interfaces.
- Motors are disabled at boot.
- Commands are validated before execution.
- Manual movement requires an authorized operator and a live dead-man mechanism.
- Autonomous operation remains disabled until the later IR integration phase.
- Remote access must use authenticated application routes; raw motor interfaces are never exposed to the network.

## Inter-process communication

Local Rithum processes communicate using **JSON messages over Unix Domain Sockets (UDS)**.

The protocol defines a common envelope containing:

- Protocol version.
- Unique message ID and optional correlation ID.
- Sender sequence number.
- Source and target component.
- Message type and action.
- Action-specific payload.
- Optional metadata.
- Raspberry Pi local timestamp with explicit UTC offset.

Transport framing uses a four-byte unsigned big-endian length prefix followed by UTF-8 JSON bytes. This avoids relying on socket read boundaries, which are not message boundaries.

The full protocol specification is maintained in:

**[IPC Protocol](docs/IPC_PROTOCOL.md)**

That document is the source of truth for message schemas, message types, action names, validation, authorization, response lifecycle, timestamps, transport framing, error handling, and implementation tests. Any code that sends or receives IPC messages must follow it.

### Timestamp policy

The Raspberry Pi's system clock is authoritative for internal message timestamps. Timestamps use ISO 8601 local time with milliseconds and an explicit UTC offset. The intended system timezone is `Asia/Kolkata`, but code must obtain the configured offset dynamically rather than hardcoding it.

Monotonic clocks are used for timeouts, heartbeat expiry, and dead-man timing. Wall-clock timestamps are for human-readable records and audit logs, not safety timing.

## Operating states

The state manager defines these operating states:

```text
BOOT
SELF_TEST
IDLE
MANUAL_LOCAL
MANUAL_REMOTE
AUTONOMOUS
HUMAN_INTERACTION
DIAGNOSTICS
SAFE_STOP
FAULT
```

`AUTONOMOUS` is disabled by default and must remain unavailable until the later autonomy milestone is completed and explicitly enabled.

The state manager validates legal transitions and latches safety conditions. It does not directly operate GPIO or motor drivers; the supervisor and hardware safety layer must enforce the physical consequences of each transition.

## Development phases

The implementation is staged to keep the system testable and prevent premature hardware activation.

| Phase | Scope | Status |
|---|---|---|
| 1 | Repository foundation, configuration, state manager, initial tests, documentation | Foundation implemented; documentation should be reviewed against code. |
| 2 | Core supervisor, worker lifecycle, IPC protocol, structured logging | Next implementation phase. |
| 3 | Hardware abstraction and safety-controlled motor interface | Planned. |
| 4 | Face renderer and display management | Planned. |
| 5 | Web control interface, authentication, operator lease | Planned. |
| 6 | Manual mecanum control, calibration, local/remote UI operation | Planned. |
| 7 | IR obstacle detection, avoidance, and autonomous mode | Planned; only after Phase 6 works. |
| Later | Human interaction, voice integration, extended diagnostics, full integration | Planned. |

Do not activate autonomous movement or connect IR sensors as active control inputs before Phase 6 is complete and the later sensor integration is deliberately started.

## Repository structure

The current project layout is expected to evolve as implementation proceeds.

```text
rithum/
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── state_manager.py
│   └── supervisor.py              # planned
├── hardware/                      # hardware abstraction
├── motion/                        # mecanum motion control
├── vision/                        # camera and detection workers
├── face/
│   └── assets/
│       ├── eyes/
│       ├── mouths/
│       └── expressions/
├── voice/                         # voice/Alexa bridge
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
├── tests/
├── scripts/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONFIGURATION.md
│   ├── DEVELOPMENT.md
│   ├── HARDWARE.md
│   ├── IPC_PROTOCOL.md
│   ├── PROJECT_OVERVIEW.md
│   ├── ROADMAP.md
│   ├── SAFETY.md
│   ├── STATE_MACHINE.md
│   ├── TESTING.md
│   └── TROUBLESHOOTING.md
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── requirements.txt
└── .gitignore
```

A directory or file shown as planned may not exist yet.

## Software environment

The current development environment is:

- Ubuntu Server 26.10, ARM64.
- Python 3.14.
- Python virtual environment at `.venv/`.
- `gpiod` Python bindings using the libgpiod v2 API.
- `unittest` for the current test suite.

Use the project's virtual environment when installing or running Python dependencies.

Activate it:

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Do not assume a dependency is required merely because it is common in other robotics projects. Keep the stack small and justify new packages.

## Running tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

Run the full test suite after changing configuration, state management, protocol schemas, supervisor behavior, or safety logic.

Tests must not require motor hardware unless they are explicitly marked as hardware-integration tests. Unit tests should use mocks or simulated interfaces.

## Configuration and safety defaults

The system must fail safe:

- Motors disabled at boot.
- IR sensors disabled until the autonomy phase.
- Autonomy disabled by default.
- Web authentication required.
- Web server bound to localhost by default until an explicit network deployment configuration is applied.
- No direct public exposure of the IPC socket or motor interfaces.
- Hardware faults and emergency-stop conditions take precedence over ordinary commands.

Do not weaken these defaults to make a test pass. Fix the test setup or implementation instead.

## Documentation index

| Document | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Overall process and component architecture. |
| [Configuration](docs/CONFIGURATION.md) | Configuration fields and environment overrides. |
| [Development](docs/DEVELOPMENT.md) | Local development workflow and conventions. |
| [Hardware](docs/HARDWARE.md) | Hardware assumptions, wiring, and interface notes. |
| [IPC Protocol](docs/IPC_PROTOCOL.md) | JSON message schema, message types, actions, validation, transport, and response lifecycle. |
| [Project Overview](docs/PROJECT_OVERVIEW.md) | Project goals and system overview. |
| [Roadmap](docs/ROADMAP.md) | Phases and planned milestones. |
| [Safety](docs/SAFETY.md) | Safety priorities, interlocks, and fail-safe behavior. |
| [State Machine](docs/STATE_MACHINE.md) | Operating states and legal transitions. |
| [Testing](docs/TESTING.md) | Test strategy and execution. |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common development and system issues. |
| [Contributing](CONTRIBUTING.md) | Contribution and change expectations. |
| [Security](SECURITY.md) | Security expectations and reporting. |

## Current verification

At the time this README was prepared, the existing configuration and state-manager test suite contained **23 passing tests**. Re-run the test command above to verify the current checkout; do not treat a historical test result as proof that later changes still pass.

## Contributing

Before implementing a new worker or subsystem:

1. Read the architecture and relevant subsystem documentation.
2. Define its responsibilities and authority boundaries.
3. Define its IPC actions and payload schema in `docs/IPC_PROTOCOL.md` if it communicates across process boundaries.
4. Add validation and tests before connecting real hardware.
5. Keep safety defaults intact.
6. Update documentation in the same change as behavior changes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow.

## License

No license is declared here. Add a license file and update this section only after the repository owner has selected the project's license.
