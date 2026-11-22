# Development Roadmap

## 1. Roadmap rules

The sequence below is a development plan, not a claim that the phases are already complete. A phase is complete only when its acceptance criteria are met and recorded.

The most important sequencing rule is:

**Manual UI-controlled movement comes first. IR-based autonomy is introduced only after Phase 6 has passed.**

## 2. Phase 1 — Project foundation

Scope:
- repository structure;
- Python virtual environment;
- configuration model and validation;
- operating-state manager;
- unit tests;
- initial documentation.

Acceptance criteria:
- configuration prints clearly;
- invalid configuration is rejected;
- state transitions match the documented graph;
- E-stop/fault latches and recovery paths are tested;
- complete unit suite passes;
- no motor output is energized by this phase.

Recorded status: configuration and state manager were implemented; 23 tests passed in the recorded baseline.

## 3. Phase 2 — Supervisor and lifecycle

Planned scope:
- supervisor process;
- worker lifecycle and health monitoring;
- structured logging;
- IPC over Unix Domain Sockets;
- state coordination;
- safe startup/shutdown;
- process crash handling.

Acceptance criteria:
- workers can be started/stopped deterministically;
- malformed IPC messages are rejected;
- supervisor failure does not leave motor outputs enabled;
- all hardware outputs remain disabled at boot;
- worker failure is visible in diagnostics.

## 4. Phase 3 — Hardware abstraction and motor driver integration

Planned scope:
- `gpiod` v2-based GPIO abstraction;
- Cytron MDD10A interface;
- four motor channel mapping;
- safe enable/disable behavior;
- optional encoder test support.

Acceptance criteria:
- no direct GPIO calls from web/UI code;
- one motor can be tested independently;
- all four motor channels have verified mapping and polarity;
- hardware E-stop works independently of Python;
- wheels-raised tests pass;
- stop behavior is measured and documented.

Encoders are optional test instrumentation and do not need to be permanently connected in the initial movement phase.

## 5. Phase 4 — Manual control interface

Planned scope:
- backend API and WebSocket command channel;
- PC-friendly responsive controller;
- mobile-friendly landscape controller;
- local touchscreen controller;
- command validation;
- one operator lease;
- heartbeat/dead-man timeout.

Acceptance criteria:
- all interfaces use the same backend command path;
- no client can bypass state/safety checks;
- simultaneous operators are handled explicitly;
- stale commands are rejected;
- disconnect and heartbeat expiry stop movement;
- local display behavior follows local-vs-remote control rules.

## 6. Phase 5 — Face, display, and human interaction

Planned scope:
- lightweight Wayland display session;
- face renderer;
- sprite-sheet and procedural animation;
- local touch mode switch between face and controller;
- camera acquisition;
- human presence/face detection;
- expression events.

Acceptance criteria:
- face renderer does not own motion authority;
- remote control does not unnecessarily replace the local face display;
- entering human-interaction mode stops movement according to policy;
- camera failure does not affect motor safety;
- UI and face processes can restart independently.

## 7. Phase 6 — End-to-end manual system validation

Planned scope:
- integrate supervisor, hardware, manual UI, display, and safety;
- validate LAN and remote access;
- validate power behavior and thermal stability;
- test stop-on-disconnect and physical E-stop.

Acceptance criteria:
- manual movement works from PC, mobile, and local touchscreen;
- all movement commands are bounded and validated;
- only one operator controls at a time;
- E-stop and disconnect behavior are verified;
- reboot starts with motor outputs disabled;
- full test suite passes;
- test results and known limitations are recorded.

**IR-based autonomy is not introduced before this phase is complete.**

## 8. Phase 7 — IR sensor integration and reactive obstacle response

Planned scope:
- install four IR obstacle sensors;
- verify output electrical compatibility;
- front/rear directional sensing;
- sensor freshness and failure detection;
- obstacle-aware manual command limiting;
- reactive avoidance behavior.

Acceptance criteria:
- each sensor is individually tested;
- sensor readings have known active polarity and range;
- stale/disconnected sensors are not interpreted as clear space;
- movement is blocked or constrained when an obstacle is detected in the relevant direction;
- manual mode also respects obstacle safety;
- autonomy remains disabled until the complete sensor test gate passes.

## 9. Phase 8 — Autonomous mode

Planned scope:
- enable autonomous state only after IR integration;
- implement bounded reactive navigation;
- expose autonomy selection in UI;
- log decisions and sensor readings;
- provide immediate manual override and stop.

Acceptance criteria:
- supervisor confirms all required sensors are healthy;
- autonomy cannot be enabled through a client-side flag alone;
- mode changes are audited;
- manual override works;
- E-stop always has priority;
- tests cover blocked paths, sensor faults, and conflicting readings.

This phase is reactive obstacle avoidance, not full SLAM or map-based navigation.

## 10. Phase 9 — Voice/Alexa integration and refinement

Planned scope:
- Alexa Skill request integration for robot-specific commands;
- request verification;
- command translation into safe high-level intents;
- face reactions to voice/skill events;
- audio activity detection where useful.

Important constraint: the Echo Dot's general Alexa audio/transcript stream is not automatically exposed to the Pi. General questions remain Alexa's responsibility; robot-specific actions use a custom integration path. Do not claim word-level mouth synchronization without a supported transcript/phoneme source.

## 11. Change control

A phase should not be marked complete because the code compiles. Require:
- acceptance tests;
- safety review;
- hardware evidence where applicable;
- updated docs;
- known limitations;
- commit reference.
