# Rithum — Agent Instructions

Read this file before changing the repository. `GEMINI.md` adds Antigravity-specific workflow rules.

## Project
- Name: Rithum; aliases: r1t-hum, rit-hum, Humanoid, rover.
- Four-wheel mecanum rover.
- Target: Raspberry Pi 5 Model B, 8 GB, Ubuntu Server 26.10 ARM64.
- Repository: https://github.com/Siddharth-Balakrishnan/rithum
- Use the actual repository path reported by `pwd`; do not assume it.
- Python-based, single-SBC architecture. Do not add another MCU, Docker, React, a local LLM, or heavyweight GUI frameworks without owner approval.

## Non-negotiable safety rules
1. Motors must remain disabled at boot and throughout software development/tests unless the owner explicitly authorizes a controlled hardware test.
2. Emergency stop and hardware faults override every ordinary command.
3. The supervisor is the sole authority for operating-state transitions, worker lifecycle, operator authorization, and motion permission.
4. Never expose raw GPIO or motor-driver controls to the network.
5. Never trust an IPC `source` field as authentication. Authenticate the local peer independently and map peer credentials to component identity.
6. Do not weaken validation or production APIs merely to satisfy tests.
7. Do not invent GPIO pins, wiring, motor-driver details, battery ratings, or sensor electrical characteristics. Ask for verified specifications.
8. Raspberry Pi GPIO is 3.3 V. Never connect a 5 V signal directly; verify sensor output type and use appropriate level shifting/pull-ups.
9. **Autonomous movement is disabled until Phase 6 is completed, verified, and the owner approves the next phase.** IR sensors and autonomy must not be activated before then.
10. IR sensors are for obstacle detection/avoidance, not line following or mapping.
11. Encoders are temporary test instrumentation; permanent operation must not depend on them.
12. Do not run destructive commands, change system services, boot/network/firewall settings, install/remove system packages, or alter persistent data without explicit approval.
13. Do not operate as root for ordinary development. Use the `r1t-hum` Linux account. Elevate only for approved administration.
14. If a request conflicts with these rules, stop and explain the conflict before editing.

## Hardware and behavior decisions
- Raspberry Pi 5 Model B, 8 GB; Ubuntu Server 26.10 ARM64, CLI-first.
- A 7-inch touchscreen is planned; a 1080p Samsung TV is used for initial display testing.
- HDMI plus USB touchscreen.
- Echo Dot 5 for Alexa/audio.
- Webcam for human detection; four adjustable IR obstacle sensors planned (front-left, front-right, rear-left, rear-right).
- Main 14.8 V, 10 Ah battery for electronics and motor drivers. A separate regulated source/power bank for Pi and touchscreen was planned. Do not change the power design without review.
- Initial movement is UI-controlled: PC browser, mobile browser, and local touchscreen.
- Local display normally shows the animated face. Local touchscreen interaction can switch to control UI; remote control leaves the face displayed.
- Human detection starts with presence/motion and face detection; gestures are later work.
- Face-box size is only an approximate proximity signal, not calibrated distance.
- Alexa handles general questions; Rithum handles robot-specific commands and expressions. A custom Alexa Skill can deliver robot commands. Do not assume Echo Dot exposes native conversation transcripts/audio to the Pi. VAD can drive approximate mouth animation, not phoneme-accurate lip sync.

## Software architecture
- Python supervisor managed by systemd.
- Separate native Linux worker processes for independently managed subsystems.
- Unix Domain Sockets (UDS) for local IPC.
- UTF-8 JSON messages with a four-byte unsigned big-endian length prefix.
- FastAPI, WebSockets, vanilla JS/CSS, SQLite for web control.
- Face renderer: lightweight Wayland + Python/Pyglet with hardware acceleration where practical; SDL2 fallback. Avoid Chromium kiosk, Electron, Unity unless approved.
- OpenCV for initial camera processing.
- `gpiod` v2 API for GPIO.
- No hardware initialization at import time. Hardware access must be behind injectable interfaces.

IPC component names: `supervisor`, `web_controller`, `motion_controller`, `face_renderer`, `vision_worker`, `voice_bridge`, `diagnostics`, `hardware_manager`.

Read `docs/IPC_PROTOCOL.md` before changing `core/ipc/`. Current protocol details include version 1.0, 64 KiB frame limit, bounded JSON envelopes, event-only broadcast, restricted socket permissions, and monotonic time for timeouts.

Known IPC hardening items that must not be represented as solved without code/tests:
- Sequence tracking currently resets per connection; process-session identity and replay protection need attention.
- Claimed `source` is not authenticated unless peer credentials are mapped to component identity.
- Server shutdown should cleanly join/stop connection-handler threads.

## Operating state machine
States: `BOOT`, `SELF_TEST`, `IDLE`, `MANUAL_LOCAL`, `MANUAL_REMOTE`, `AUTONOMOUS`, `HUMAN_INTERACTION`, `DIAGNOSTICS`, `SAFE_STOP`, `FAULT`.

Face/display states are separate: `FACE_IDLE`, `FACE_STATIC`, `FACE_RANDOM`, `FACE_HUMAN`, `DISPLAY_UI`.

Priority:
1. Emergency stop / hardware faults.
2. Obstacle safety (after IR integration).
3. Human interaction.
4. Manual local / remote.
5. Autonomous (only after Phase 6 and approval).
6. Idle animation.

Idle, diagnostics, human interaction, safe stop and fault states must not permit movement. The state manager records policy/state; it does not directly drive GPIO or motors. Physical safety must be enforced by supervisor and hardware safety layer.

Motion authorization must check:
- State permits movement.
- No E-stop latch or fault.
- Hardware initialized and motor enable explicitly authorized.
- Authenticated operator lease is valid.
- Dead-man heartbeat is current.
- Command is valid, bounded, and not expired.
- Available obstacle interlocks permit movement.
- Speed/acceleration limits are enforced.

Current design targets, not certified safety values: motion dead-man timeout about 0.4 s; operator heartbeat timeout about 1.0 s. Use monotonic time. On disconnect, lease expiry, worker failure, or invalid authorization, stop and disable motor outputs.

## Roadmap and phase gates
1. Foundation: config, state manager, IPC.
2. Supervisor: startup/shutdown, state coordination, IPC dispatch, worker lifecycle, faults.
3. Hardware abstraction/safety: GPIO abstraction, motor interlocks, E-stop, diagnostics; no energized motors during software tests.
4. Motion: mecanum kinematics and bounded manual commands; encoders temporary only.
5. Web control: FastAPI, auth, operator lease, WebSockets, PC/mobile/local UI.
6. Manual movement integration: UI-to-supervisor-to-motion-to-hardware; verify manual movement and fail-safe stopping.
7. IR and autonomy: only after Phase 6 is completed and owner-approved. Add obstacle sensors/interlocks, reactive avoidance, then explicitly gated autonomy.
8. Vision and voice.
9. Deployment/hardening: systemd, permissions, logging, recovery, security, hardware validation.

Do not skip gates or silently combine milestones.

## Repository and baseline
Expected folders: `core/`, `hardware/`, `motion/`, `vision/`, `face/`, `voice/`, `web/`, `diagnostics/`, `storage/`, `config/`, `tests/`, `docs/`.

Existing modules include `core/config.py`, `core/state_manager.py`, and `core/ipc/{models,validator,framing,server,client}.py`.

Historical test checkpoint: 56 tests passed (9 config, 14 state manager, 33 IPC). This is not proof the current checkout passes. Run tests before and after edits.

## Coding standards
- Type hints on public interfaces; small functions and explicit interfaces.
- Hardware-independent, deterministic tests by default.
- Validate external inputs at boundaries.
- Use monotonic clocks for elapsed time, deadlines and leases.
- Centralize and validate configuration.
- Structured logging; never silently swallow exceptions.
- No secrets in source control.
- Do not commit databases, logs, virtual environments, credentials, or caches.
- Add tests for normal, invalid, authorization-failure, and cleanup/failure paths.
- Explain and justify new dependencies.
- Preserve public APIs unless a justified change is required; update call sites and tests together.

## Required agent workflow
Before edits:
1. Read this file and relevant architecture/safety docs.
2. Inspect `pwd`, Git status, recent commits, and current implementation.
3. Identify exact files/interfaces, risks, and test plan.
4. Propose the plan before editing.
5. Ask approval for privileged, destructive, hardware, network, or system-level actions.

During edits:
- One milestone/task at a time.
- Never overwrite uncommitted user changes.
- No root/sudo for ordinary code work.
- No motor energizing or autonomy.
- Keep diffs focused and add tests with behavior changes.

After edits:
- Run focused tests, then the full suite: `pytest -v -ra --tb=short`.
- Run `git diff --check`, inspect `git diff` and `git status --short`.
- Report files changed, behavior, exact test results, limitations, and hardware tests still required.
- Do not commit or push unless explicitly requested.
- Stop for owner review before the next milestone.

## Next expected task
Unless the owner says otherwise, the next milestone is `core/supervisor.py`.

Before implementing:
- Inspect config, state manager, and every IPC module.
- Read `docs/IPC_PROTOCOL.md`, `docs/ARCHITECTURE.md`, `docs/SAFETY.md`, and `docs/STATE_MACHINE.md` if present.
- Propose supervisor API, lifecycle, dispatch, authorization, and failure behavior first.
- Keep supervisor hardware-independent and testable.
- Do not expand scope into GPIO, motors, web UI, vision, or autonomy.
