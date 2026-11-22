# Project Overview

## 1. Purpose

Rithum is a Raspberry Pi 5-based mecanum rover project. It is intended to combine omnidirectional manual movement, a local visual face, remote/local control interfaces, voice interaction, human-aware interaction, and later reactive obstacle avoidance.

This document defines project scope and terminology. It does not claim that every described subsystem has been implemented.

## 2. Project objectives

### Core objectives

- Control four DC geared motors through two dual-channel motor drivers.
- Use four mecanum wheels to support translation and rotation.
- Provide a responsive PC/mobile control interface and a local touchscreen interface.
- Keep motor control behind a trusted backend and safety layer.
- Maintain a clear operating state and a traceable state-transition history.

### Later objectives

- Render a lightweight animated face on the robot display.
- Detect human presence and, where practical, faces using a camera.
- Integrate Alexa for voice interaction and robot-specific commands.
- Use four IR sensors for obstacle detection and reactive avoidance.
- Add autonomous operation only after the manual system and sensor integration are stable.

## 3. Scope boundaries

### In scope

- Raspberry Pi 5 as the main computer.
- Ubuntu Server/Linux environment.
- Python backend and hardware integration.
- Local and remote web-based control.
- GPIO interfacing through the Linux GPIO character-device API (`gpiod` v2).
- Mecanum motion control.
- Local display/face rendering.
- Camera and IR sensor integration.
- Process supervision, logging, diagnostics, and tests.

### Out of scope for the current design

- A second microcontroller as the primary motor controller.
- Docker-based deployment.
- Publicly exposed unauthenticated motor APIs.
- Full SLAM or map-based navigation as part of the first obstacle-avoidance implementation.
- Autonomous movement before the IR phase is complete.
- Treating the Alexa Echo Dot as a raw microphone/speaker peripheral whose complete audio/transcript stream is automatically available to the Pi.

## 4. Terminology

| Term | Meaning |
|---|---|
| Rithum | Project/robot name. |
| `r1t-hum` | Hostname used by the Raspberry Pi. |
| SBC | Single-board computer; the Raspberry Pi 5 in this project. |
| Mecanum drive | Four-wheel arrangement with angled rollers that allows lateral movement. |
| Operating state | Backend state such as `IDLE`, `MANUAL_LOCAL`, or `SAFE_STOP`. |
| Face state | Visual expression/animation state; separate from operating state. |
| Supervisor | Intended process that owns service lifecycle, state coordination, and safety enforcement. |
| Dead-man heartbeat | Repeated signal from the active controller; loss of heartbeat causes motion to stop. |
| Operator lease | Exclusive time-limited authority for one authenticated controller to command movement. |
| Reactive avoidance | Short-range obstacle response using sensor readings; not a global map or SLAM system. |
| E-stop latch | Software record that emergency stop was triggered; physical output interruption must be separate. |

## 5. Development sequence

The system is being built in layers:

1. Repository, configuration, state model, and tests.
2. Supervisor and safe process lifecycle.
3. Hardware abstraction and motor-driver integration with wheels raised.
4. Local/remote manual controller.
5. Display/face and human interaction.
6. End-to-end manual-control validation and safety verification.
7. IR sensor integration and obstacle response.
8. Autonomous mode, enabled only after the preceding gate is passed.

The exact task breakdown is maintained in [ROADMAP.md](ROADMAP.md).

## 6. What is implemented today?

The verified software foundation includes:

- `core/config.py`: typed configuration sections, environment-variable loading, validation, and readable configuration output.
- `core/state_manager.py`: operating-state transitions, emergency-stop/fault latches, recovery checks, and transition history.
- `tests/test_config.py`: configuration tests.
- `tests/test_state_manager.py`: state-manager tests.

The initial complete test run reported 23 passing tests. Re-run tests before treating this as the current status.

Subsystem directories such as `hardware/`, `motion/`, `vision/`, `voice/`, and `web/` are scaffolding until actual implementation files and tests are present.

## 7. Design constraints

- The Pi is not a real-time motor-control MCU. Motion code must use conservative update rates, bounded commands, timeouts, and a hardware-safe disable path.
- Linux scheduling and network latency are variable. Do not depend on a single network message to stop a moving robot.
- GPIO is 3.3 V logic. Electrical compatibility must be verified for every attached board and sensor.
- Mecanum movement depends on correct motor orientation, wheel handedness, and sign conventions. These must be calibrated physically.
- The robot must be safe when a process crashes, the network drops, or the Pi reboots.

## 8. Related documents

- [Architecture](ARCHITECTURE.md)
- [State machine](STATE_MACHINE.md)
- [Hardware](HARDWARE.md)
- [Safety](SAFETY.md)
- [Roadmap](ROADMAP.md)
