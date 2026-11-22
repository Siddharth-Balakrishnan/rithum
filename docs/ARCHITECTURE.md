# Architecture

## 1. Status and interpretation

This document describes the intended architecture. Only the configuration and state-manager foundation is currently verified as implemented. Treat process names, APIs, sockets, and service units below as design contracts to implement—not as proof that those components already exist.

## 2. Architectural goals

1. Keep one Raspberry Pi 5 as the central compute platform.
2. Use native Linux processes managed by `systemd`; no Docker requirement.
3. Separate hardware access from web/UI code.
4. Give one supervisor authority over operating modes and worker lifecycle.
5. Use validated inter-process messages rather than shared mutable globals.
6. Fail safely when a worker, network connection, or controller disappears.
7. Keep manual control operational before enabling autonomous behavior.

## 3. Target component responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| Supervisor | Start/stop workers, coordinate state, enforce operational policy, react to worker failure. | Expose unrestricted hardware access to clients. |
| State manager | Validate operating-state transitions and record history. | Directly manipulate GPIO or motor outputs. |
| Safety manager | Enforce E-stop, fault, motor-disable, heartbeat, and obstacle interlocks. | Trust a browser-provided claim that hardware is safe. |
| Hardware layer | Encapsulate GPIO, motor drivers, sensors, and optional encoders. | Contain web authentication or UI logic. |
| Motion worker | Convert bounded motion commands into wheel-level outputs. | Accept unvalidated public network commands. |
| Web/API service | Authenticate clients, serve UI, validate request shape, manage operator lease, forward commands. | Access GPIO or bypass the supervisor. |
| Face renderer | Render expression and animation state. | Own movement authority. |
| Vision worker | Camera acquisition and human/face observations. | Directly authorize movement. |
| Voice/Alexa bridge | Translate approved voice/skill events into high-level intents. | Bypass command validation and safety checks. |
| Diagnostics | Collect health, hardware enumeration, logs, and test results. | Energize hardware as a side effect of a read-only check. |

## 4. Process and IPC model

The intended IPC mechanism is Unix Domain Sockets with structured JSON messages. This is a local machine boundary, not a security boundary by itself. Socket permissions, message validation, peer identity where appropriate, and request authorization are still required.

A message should include at least:

- message type;
- protocol version;
- request/correlation ID;
- sender identity or worker name;
- timestamp or monotonic-age information where relevant;
- payload validated against a strict schema.

Reject unknown message types, malformed JSON, oversized messages, invalid numeric ranges, stale commands, and commands that are not legal in the current state.

Do not use arbitrary Python object deserialization (for example, `pickle`) across IPC.

## 5. Intended command path

```text
Controller UI
    │
    ▼
Authenticated API/WebSocket
    │
    ├── Validate schema and numeric limits
    ├── Verify active operator lease
    ├── Verify command freshness / heartbeat
    ▼
Supervisor command interface
    │
    ├── Check operating state
    ├── Check safety interlocks
    ├── Check obstacle policy (after IR phase)
    ▼
Motion worker
    │
    ▼
Hardware abstraction
    │
    ▼
Motor drivers
    │
    ▼
Four motors
```

Every command path—local touchscreen, LAN, Tailscale, or any future remote tunnel—must converge on the same backend validation and safety checks.

## 6. Operating state vs. face state

These are separate state domains.

**Operating state** answers: what is the robot allowed to do? Examples: `IDLE`, `MANUAL_LOCAL`, `MANUAL_REMOTE`, `SAFE_STOP`.

**Face state** answers: what should the display render? Examples planned include idle animation, static face during movement, human-aware expression, and warning expression.

Do not encode motor permission in a face animation state. A display transition must never implicitly enable motion.

## 7. Local and remote UI behavior

- PC and mobile browsers are clients of the same API.
- The local touchscreen can display the control UI when a local user explicitly activates it.
- Remote control should not automatically replace the face on the robot's local display.
- When the local display is in face mode, remote control can still be active.
- Only one authenticated operator should hold movement authority at a time.
- Observers may be allowed to view status, but must not issue motion commands.

## 8. Operator lease and dead-man behavior

The intended design uses an exclusive operator lease:

1. A client authenticates.
2. The backend grants a time-limited control lease if no other operator owns it.
3. The client sends periodic heartbeats while actively controlling.
4. Motion commands are accepted only while the lease is valid.
5. On lease expiry, disconnect, stale heartbeat, or explicit release, the supervisor commands a stop and disables outputs as required.
6. A second operator cannot silently take over a live lease.

Initial tuning notes discussed a remote dead-man interval around 300–500 ms and an operator heartbeat timeout around 1 second. These are starting values only. They must be tested under real network conditions and must not replace an independent hardware E-stop.

## 9. Networking and trust boundaries

- Bind the development web service to `127.0.0.1` by default.
- LAN access requires explicit configuration and application authentication.
- Tailscale or a protected tunnel can provide transport reachability, but does not replace application authorization.
- Never expose raw GPIO, motor-driver pins, or an unauthenticated movement endpoint to the public Internet.
- Alexa skill requests require their own request verification/signature validation.

## 10. Failure handling

| Failure | Required behavior |
|---|---|
| Web client disconnects during motion | Expire lease/heartbeat and stop motion. |
| Motion worker crashes | Supervisor disables motor outputs and enters a safe state. |
| Supervisor crashes | Hardware should default to disabled; an independent physical E-stop remains available. |
| Invalid command | Reject and log; do not partially apply it. |
| Sensor read becomes stale | Treat the reading as invalid; do not assume the path is clear. |
| Camera worker crashes | Degrade vision only; do not affect motor safety. |
| Face renderer crashes | Restart/display failure; do not affect motor safety. |
| Network tunnel disappears | Remote control is lost; stop on lease/heartbeat expiry. |
| Pi reboots | Motor outputs remain disabled at boot. |

## 11. Implementation guidance

Build and test each boundary independently:

1. State manager and configuration.
2. Supervisor with fake workers.
3. IPC schema and invalid-message tests.
4. Hardware abstraction with mock GPIO.
5. Motion mixing and motor-driver tests without wheels on the floor.
6. API authentication and lease tests.
7. Physical integration with wheels raised.
8. Full system integration only after component tests pass.
