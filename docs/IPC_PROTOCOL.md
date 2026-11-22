# Rithum Inter-Process Communication (IPC) Protocol

**Document:** `docs/IPC_PROTOCOL.md`  
**Protocol name:** `rithum-ipc`  
**Protocol version:** `1.0`  
**Status:** Proposed specification for implementation  
**Applies to:** Local Rithum processes communicating through Unix Domain Sockets

---

## 1. Purpose

This document defines the message protocol used by Rithum processes to communicate with the central supervisor.

The protocol standardizes:

- The JSON message envelope and its required fields.
- Message types and action names.
- Routing and sender identity.
- Payload conventions.
- Validation and authorization requirements.
- Request acknowledgement, completion, rejection, and failure.
- Message ordering, duplicate handling, timeouts, and timestamps.
- Transport framing over Unix Domain Sockets.
- Logging and diagnostic expectations.

The intent is to make communication predictable and inspectable. A developer should be able to read a message in a log and determine who sent it, who should receive it, what operation was requested, what data was supplied, and how the request ended.

This document defines the protocol contract. It does **not** mean every listed action is already implemented.

## 2. Scope and architecture

### 2.1 Logical architecture

Rithum uses a single-board-computer architecture. The supervisor is the central authority for process lifecycle and operating-state coordination.

Expected local participants include:

| Component | Responsibility |
|---|---|
| `supervisor` | Validates messages, coordinates workers, owns operating-state transitions, and applies safety policy. |
| `web_controller` | Sends authenticated operator requests and receives status/results. |
| `motion_controller` | Executes authorized movement requests through the hardware abstraction layer. |
| `face_renderer` | Displays expressions, animations, and display states. |
| `vision_worker` | Reports camera and human-detection events. |
| `voice_bridge` | Bridges supported Alexa/voice events into Rithum. |
| `diagnostics` | Runs approved diagnostics and reports results. |
| `hardware_manager` | Reports hardware state and mediates hardware access under supervisor policy. |

The names above are logical component identities. A component may be split into multiple processes later, but its identity must remain unambiguous.

### 2.2 Transport versus serialization

These are separate concerns:

- **Serialization:** JSON encoded as UTF-8.
- **Transport:** Unix Domain Sockets (UDS) for local process communication.
- **Framing:** A four-byte unsigned big-endian length prefix followed by exactly that many UTF-8 JSON bytes.

Do not assume that one socket `recv()` call returns one complete message. Stream sockets do not preserve application message boundaries. The receiver must read the complete length prefix and then exactly the declared payload length.

### 2.3 Authority boundary

The supervisor is the authority for:

- Accepting or rejecting operating-state transitions.
- Starting, stopping, and restarting managed workers.
- Granting operational permissions.
- Enforcing operator leases and command expiry.
- Applying safety policy before movement is enabled.
- Coordinating safe-stop and fault handling.

A worker must not grant itself authority by sending a message that claims a higher privilege. A message's `source`, `priority`, or payload is not proof of identity or authorization.

The web controller must never access motor GPIO or motor-driver interfaces directly. It requests operations from the supervisor, which validates the request and coordinates the motion subsystem.

## 3. Design principles

1. **Explicitness:** Every message states its sender, recipient, type, action, and payload.
2. **Validation before execution:** Parse and validate the complete message before dispatching it.
3. **Least privilege:** Each component may send only the actions permitted for its role.
4. **Supervisor authority:** Only the supervisor authorizes operating-state transitions and worker lifecycle operations.
5. **Safety over convenience:** Invalid, stale, unauthorized, or ambiguous movement requests fail closed.
6. **Traceability:** Every message has a unique ID; every response refers to the request it answers.
7. **Bounded resources:** Message size, payload size, timeouts, and queue sizes must be bounded.
8. **Versioning:** Protocol changes must be explicit and backward compatibility must not be assumed.
9. **Local clock authority:** The Raspberry Pi system clock supplies message timestamps.
10. **No implicit success:** Receipt, acceptance, and completion are distinct outcomes.

## 4. Canonical message schema

### 4.1 Standard envelope

All protocol messages use the following envelope:

```json
{
  "protocol_version": "1.0",
  "message_id": "01934f7a-8b21-7c42-a6d1-123456789abc",
  "correlation_id": null,
  "sequence": 1042,
  "source": "web_controller",
  "target": "supervisor",
  "message_type": "COMMAND",
  "action": "SET_OPERATING_STATE",
  "payload": {
    "state": "MANUAL_LOCAL"
  },
  "metadata": {
    "priority": "NORMAL",
    "requires_response": true,
    "timeout_ms": 2000
  },
  "timestamp": "2026-11-22T18:40:31.245+05:30"
}
```

The example is illustrative. The UUID, sequence number, timestamp, and payload must be generated or validated at runtime.

### 4.2 Field definitions

| Field | Type | Required | Description |
|---|---|---:|---|
| `protocol_version` | string | Yes | Protocol version, currently `1.0`. |
| `message_id` | string | Yes | Unique identifier for this individual message. UUID format is recommended. |
| `correlation_id` | string or null | Yes | ID of the message this message relates to. `null` for a new request/event; set to the originating request's `message_id` for responses and related follow-up messages. |
| `sequence` | integer | Yes | Monotonically increasing sequence generated by the sending process for its outgoing message stream. Starts at 1 after process start. |
| `source` | string | Yes | Registered identity of the sending component. |
| `target` | string | Yes | Intended recipient identity, or a documented broadcast target such as `broadcast`. |
| `message_type` | string | Yes | One of the message types defined in Section 5. |
| `action` | string | Yes | Action identifier valid for the selected message type. |
| `payload` | object | Yes | Action-specific data. Use `{}` when no data is required. |
| `metadata` | object | Yes | Transport/execution metadata. Use `{}` when no metadata is required. |
| `timestamp` | string | Yes | Creation/acceptance timestamp from the Pi's local system clock, including UTC offset. |

Unknown top-level fields must be rejected in protocol version 1.0 unless explicitly permitted by a later schema revision. This avoids silently accepting misspelled or misunderstood fields.

### 4.3 Identifier rules

- `message_id` must be unique among messages generated by a process and should be a UUID.
- A response must have its own new `message_id`.
- A response's `correlation_id` must equal the request's `message_id`.
- `correlation_id` is not a replacement for `message_id`.
- A message must not reuse an earlier ID to simulate a retry. A retry is a new message with a new `message_id` and the same `correlation_id` or an explicit idempotency key, according to the action's retry policy.
- Sequence numbers are scoped to a sender identity and process session. They are not globally unique.

For robust process restarts, a future implementation may add a `sender_session_id`. Until then, sequence continuity must not be assumed across process restarts.

### 4.4 Source and target

`source` and `target` use registered component identifiers, lowercase snake case.

Initial registered identities:

```text
supervisor
web_controller
motion_controller
face_renderer
vision_worker
voice_bridge
diagnostics
hardware_manager
```

The list may grow through documented changes. Arbitrary source names must not be accepted.

`broadcast` may be used only for event distribution where the event definition explicitly permits it. Commands must have one concrete target. A broadcast command is invalid.

### 4.5 Payload conventions

- `payload` must always be a JSON object, never a scalar, array, or `null`.
- Payload keys use lowercase snake case.
- Payload schemas are action-specific.
- Reject unexpected payload keys unless that action explicitly allows extension fields.
- Numeric values must be finite. Reject NaN and positive/negative infinity.
- Units must be explicit in field names or action documentation, e.g. `duration_ms`, `speed_percent`, `distance_mm`.
- Avoid ambiguous values such as `speed: 0.5` without defining the scale.
- Do not place credentials, passwords, session cookies, API tokens, or private keys in IPC payloads or logs.

### 4.6 Metadata conventions

Version 1.0 defines these optional metadata fields:

| Field | Type | Meaning |
|---|---|---|
| `priority` | string | `LOW`, `NORMAL`, `HIGH`, or `CRITICAL`. |
| `requires_response` | boolean | Whether the sender expects a response message. |
| `timeout_ms` | integer | Requested processing deadline in milliseconds. |
| `idempotency_key` | string | Optional key for safely identifying a retry of an operation. |
| `trace_id` | string | Optional identifier grouping multiple messages into one diagnostic trace. |

`metadata` itself is required and must be an object. Individual metadata fields are optional.

Priority is a scheduling hint, not an authorization or safety override. A sender cannot make an unsafe command valid by assigning `CRITICAL`.

The supervisor may clamp `timeout_ms` to configured limits. It must not permit an untrusted sender to request unbounded execution time.

## 5. Allowed message types

Message types are uppercase strings. Version 1.0 defines the following.

### 5.1 `COMMAND`

Requests that a recipient perform an operation.

Examples:

- `SET_OPERATING_STATE`
- `MOVE`
- `STOP`
- `SET_EXPRESSION`
- `START_WORKER`

Commands are subject to schema validation, sender authorization, state-machine policy, safety checks, and deadline checks.

### 5.2 `RESPONSE`

Reports the immediate disposition of a command or a result when the action completes synchronously.

A response must contain a `correlation_id` referring to the request's `message_id`.

Recommended response payload statuses:

- `RECEIVED`: The message was parsed and accepted into the request-processing path. This does not mean the operation is authorized.
- `ACCEPTED`: The request passed validation and policy checks and may execute.
- `REJECTED`: The request was refused before execution.
- `COMPLETED`: The requested operation completed successfully.
- `FAILED`: The request was accepted but execution failed.

Not every command needs every status. For a synchronous operation, the implementation may return one final response. For a longer operation, use an early `ACCEPTED` response followed by a later `COMPLETED` or `FAILED` response.

### 5.3 `EVENT`

Reports that something happened. Events are not requests to perform an operation.

Examples:

- `STATE_CHANGED`
- `HUMAN_DETECTED`
- `HUMAN_LOST`
- `WORKER_STARTED`
- `WORKER_STOPPED`
- `WORKER_FAILED`
- `OBSTACLE_DETECTED` (reserved for the later IR/autonomy phase)

An event may be sent to the supervisor or to `broadcast` if the event definition allows it. Events must not be interpreted as permission to change operating state or energize motors.

### 5.4 `ERROR`

Reports a protocol, routing, validation, or processing error. Errors should include a stable `error_code` and a concise human-readable `message`.

Examples:

- `MALFORMED_JSON`
- `INVALID_ENVELOPE`
- `UNSUPPORTED_PROTOCOL_VERSION`
- `UNKNOWN_SOURCE`
- `UNKNOWN_TARGET`
- `UNKNOWN_ACTION`
- `UNAUTHORIZED_ACTION`
- `INVALID_PAYLOAD`
- `MESSAGE_TOO_LARGE`
- `SEQUENCE_REPLAY`
- `REQUEST_TIMEOUT`
- `INTERNAL_ERROR`

An error message should identify the original request through `correlation_id` when one exists.

### 5.5 `HEARTBEAT`

Reports process liveness and basic health. It is not a substitute for a full health report.

A heartbeat payload should be small and bounded:

```json
{
  "status": "HEALTHY",
  "uptime_ms": 125000,
  "load_state": "NORMAL"
}
```

Allowed `status` values:

- `HEALTHY`
- `DEGRADED`
- `BUSY`

Heartbeat scheduling and expiry use monotonic time, not wall-clock timestamps. The supervisor should treat a missed heartbeat as a liveness signal requiring policy evaluation, not proof of a specific failure cause.

### 5.6 `STATUS`

Reports a component's current state or answers a status query.

Examples:

- `SYSTEM_STATUS`
- `WORKER_STATUS`
- `MOTION_STATUS`
- `HARDWARE_STATUS`
- `OPERATING_STATE`

A status message is informational. It must not itself trigger an operation.

## 6. Action registry

The following registry defines the intended version 1.0 action vocabulary. It is a design contract and implementation roadmap, not a claim that all actions currently exist.

### 6.1 System and supervisor actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `GET_SYSTEM_STATUS` | `web_controller`, `diagnostics` | `supervisor` | Request system summary. |
| `COMMAND` | `RUN_SELF_TEST` | `supervisor` | `hardware_manager`, `diagnostics` | Run approved startup checks. |
| `COMMAND` | `SHUTDOWN_SYSTEM` | `supervisor` | Local system service | Request controlled shutdown. |
| `EVENT` | `SYSTEM_READY` | `supervisor` | `broadcast` | Announce successful startup. |
| `EVENT` | `SYSTEM_SHUTTING_DOWN` | `supervisor` | `broadcast` | Announce controlled shutdown. |
| `STATUS` | `SYSTEM_STATUS` | `supervisor` | Requesting component | Return system summary. |

A remote web request must not directly invoke an operating-system shutdown command. It must pass through supervisor authorization and any required local confirmation policy.

### 6.2 Operating-state actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `SET_OPERATING_STATE` | `web_controller`, `supervisor` | `supervisor` | Request a permitted state transition. |
| `COMMAND` | `GET_OPERATING_STATE` | `web_controller`, `diagnostics` | `supervisor` | Query current operating state. |
| `EVENT` | `STATE_CHANGED` | `supervisor` | `broadcast` | Announce a committed state transition. |
| `STATUS` | `OPERATING_STATE` | `supervisor` | Requesting component | Return current state and relevant latches. |

Allowed state names are defined by the state manager:

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

Important constraints:

- `AUTONOMOUS` remains disabled until the post-Phase-6 IR integration is completed, tested, and explicitly enabled in configuration.
- A web client cannot request `SAFE_STOP` recovery or clear fault/E-stop latches by merely sending a state transition.
- `SAFE_STOP` and `FAULT` recovery must use dedicated, safety-checked supervisor workflows.
- The state manager validates legal transitions; the supervisor must also coordinate hardware actions around a transition.
- State changes must be announced only after the state manager has committed the transition.

### 6.3 Motion actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `MOVE` | `web_controller`, `supervisor` | `supervisor` or authorized motion interface | Request movement. |
| `COMMAND` | `STOP` | `web_controller`, `supervisor`, safety subsystem | `supervisor` | Request normal motion stop. |
| `COMMAND` | `EMERGENCY_STOP` | Authorized safety inputs, `supervisor`, approved controller path | `supervisor` | Trigger latched emergency stop handling. |
| `EVENT` | `MOTION_STARTED` | `motion_controller` | `supervisor` | Report movement start. |
| `EVENT` | `MOTION_STOPPED` | `motion_controller` | `supervisor` | Report movement stop. |
| `EVENT` | `MOTION_FAULT` | `motion_controller`, `hardware_manager` | `supervisor` | Report a motion-related fault. |
| `STATUS` | `MOTION_STATUS` | `motion_controller`, `supervisor` | Requesting component | Report motion subsystem state. |

A future `MOVE` payload must define the coordinate convention and units. The intended mecanum control convention should be documented before implementing movement commands, including:

- `linear_x`: forward/backward velocity or normalized command.
- `linear_y`: left/right strafe.
- `angular_z`: rotation.
- Explicit units or normalized ranges.
- Command duration or dead-man refresh semantics.

Do not implement or accept an ambiguous `speed` field. The supervisor must reject movement unless the operating state, operator lease, dead-man heartbeat, motor interlocks, and hardware readiness permit it.

`STOP` is a normal stop request. `EMERGENCY_STOP` invokes the latched safety path. Neither should depend on a normal movement command succeeding.

### 6.4 Worker lifecycle actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `START_WORKER` | `supervisor` | `supervisor` process manager | Start an approved worker. |
| `COMMAND` | `STOP_WORKER` | `supervisor` | `supervisor` process manager | Stop an approved worker. |
| `COMMAND` | `RESTART_WORKER` | `supervisor` | `supervisor` process manager | Restart an approved worker. |
| `EVENT` | `WORKER_STARTED` | Worker/process manager | `supervisor` | Report successful startup. |
| `EVENT` | `WORKER_STOPPED` | Worker/process manager | `supervisor` | Report termination. |
| `EVENT` | `WORKER_FAILED` | Worker/process manager | `supervisor` | Report unexpected failure. |
| `HEARTBEAT` | `WORKER_HEALTH` | Managed worker | `supervisor` | Report worker liveness. |
| `STATUS` | `WORKER_STATUS` | `supervisor` | Requesting component | Report worker state. |

Workers must not start, stop, or restart sibling processes themselves. Worker lifecycle is owned by the supervisor.

### 6.5 Face renderer actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `SET_EXPRESSION` | `supervisor`, authorized interaction coordinator | `face_renderer` | Set a face expression. |
| `COMMAND` | `SET_ANIMATION` | `supervisor` | `face_renderer` | Select an animation. |
| `COMMAND` | `SET_DISPLAY_MODE` | `supervisor`, local UI coordinator | `face_renderer` | Select face or local control display mode. |
| `EVENT` | `DISPLAY_MODE_CHANGED` | `face_renderer` | `supervisor` | Confirm display-mode change. |
| `STATUS` | `FACE_STATUS` | `face_renderer` | Requesting component | Report renderer state. |

Remote control must not force the local display into the control UI. The local display policy is controlled by the supervisor and local-touch interaction rules.

### 6.6 Vision actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `EVENT` | `HUMAN_DETECTED` | `vision_worker` | `supervisor` | Report human presence. |
| `EVENT` | `HUMAN_LOST` | `vision_worker` | `supervisor` | Report that a previously detected person is no longer present. |
| `EVENT` | `FACE_DETECTED` | `vision_worker` | `supervisor` | Report face detection metadata. |
| `EVENT` | `VISION_FAULT` | `vision_worker` | `supervisor` | Report camera/vision failure. |
| `STATUS` | `VISION_STATUS` | `vision_worker` | Requesting component | Report vision worker state. |

Vision events are observations, not authorization. Human detection must not grant operator privileges or independently enable movement.

### 6.7 Voice bridge actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `EVENT` | `VOICE_COMMAND_RECEIVED` | `voice_bridge` | `supervisor` | Report a verified supported robot command. |
| `EVENT` | `VOICE_ACTIVITY_STARTED` | `voice_bridge` | `supervisor` | Report detected voice activity. |
| `EVENT` | `VOICE_ACTIVITY_ENDED` | `voice_bridge` | `supervisor` | Report end of voice activity. |
| `ERROR` | `VOICE_BRIDGE_ERROR` | `voice_bridge` | `supervisor` | Report bridge failure. |
| `STATUS` | `VOICE_STATUS` | `voice_bridge` | Requesting component | Report voice integration state. |

Voice activity is not equivalent to a recognized command. A command must be authenticated/verified at the integration boundary and still pass supervisor authorization and safety policy.

### 6.8 Diagnostics and hardware actions

| Message type | Action | Permitted source | Target | Purpose |
|---|---|---|---|---|
| `COMMAND` | `RUN_DIAGNOSTIC` | `web_controller`, `supervisor` | `diagnostics` | Request an approved diagnostic. |
| `EVENT` | `DIAGNOSTIC_COMPLETED` | `diagnostics` | `supervisor` | Report diagnostic completion. |
| `EVENT` | `DIAGNOSTIC_FAILED` | `diagnostics` | `supervisor` | Report diagnostic failure. |
| `STATUS` | `HARDWARE_STATUS` | `hardware_manager` | Requesting component | Report hardware readiness. |
| `EVENT` | `HARDWARE_FAULT` | `hardware_manager` | `supervisor` | Report hardware fault. |

Diagnostics that can energize outputs, move actuators, or affect safety require explicit supervisor authorization and a safe operating context. Read-only diagnostics should be preferred.

### 6.9 Future obstacle-sensor actions

These actions are reserved for the later autonomy phase and must not be treated as active during the initial UI-only movement phases.

```text
OBSTACLE_DETECTED
OBSTACLE_CLEARED
IR_SENSOR_STATUS
OBSTACLE_AVOIDANCE_REQUESTED
```

The initial Rithum movement implementation is UI-controlled. IR-based autonomous movement is introduced only after Phase 6 is working and the sensors and safety behavior have been tested.

## 7. Response lifecycle

### 7.1 Lifecycle overview

A command follows this conceptual lifecycle:

```text
SENDER
  |
  | COMMAND
  v
SUPERVISOR RECEIVES MESSAGE
  |
  +--> Parse and frame validation
  |
  +--> Envelope/schema validation
  |
  +--> Source identity and authorization
  |
  +--> Target/action validation
  |
  +--> State and safety policy checks
  |
  +--> Deadline and duplicate checks
  |
  +--> REJECTED / ERROR, if any check fails
  |
  +--> ACCEPTED
  |
  +--> Execute or delegate operation
  |
  +--> COMPLETED or FAILED
```

### 7.2 Receipt is not acceptance

The following meanings must remain distinct:

- **Received:** Bytes arrived and a complete frame was reconstructed.
- **Parsed:** The bytes were valid UTF-8 JSON.
- **Validated:** The envelope and action-specific payload matched the schema.
- **Authorized:** The source was allowed to request the action.
- **Accepted:** The supervisor committed to processing the request.
- **Completed:** The requested operation finished successfully.
- **Failed:** An accepted operation could not complete.

A sender must not interpret socket delivery or a `RECEIVED` response as permission to move the robot.

### 7.3 Synchronous commands

For short operations, the supervisor may return one final response:

```json
{
  "protocol_version": "1.0",
  "message_id": "response-uuid",
  "correlation_id": "request-uuid",
  "sequence": 204,
  "source": "supervisor",
  "target": "web_controller",
  "message_type": "RESPONSE",
  "action": "GET_OPERATING_STATE",
  "payload": {
    "status": "COMPLETED",
    "operating_state": "IDLE"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:31.280+05:30"
}
```

### 7.4 Asynchronous commands

Long-running operations should return an early response and a later final response.

Example:

1. `RUN_DIAGNOSTIC` command arrives.
2. Supervisor validates and authorizes it.
3. Supervisor replies `ACCEPTED`.
4. Diagnostics worker runs the test.
5. Worker emits `DIAGNOSTIC_COMPLETED` or `DIAGNOSTIC_FAILED`.
6. Supervisor sends the final correlated `COMPLETED` or `FAILED` response to the original requester.

The supervisor must retain a bounded pending-request record while the operation is active. Pending requests must expire after their configured deadline.

### 7.5 Rejection response

A rejected request should include a stable code and useful context:

```json
{
  "protocol_version": "1.0",
  "message_id": "response-uuid",
  "correlation_id": "request-uuid",
  "sequence": 205,
  "source": "supervisor",
  "target": "web_controller",
  "message_type": "RESPONSE",
  "action": "SET_OPERATING_STATE",
  "payload": {
    "status": "REJECTED",
    "error_code": "AUTONOMY_NOT_ENABLED",
    "message": "AUTONOMOUS mode is unavailable in the current configuration.",
    "current_state": "IDLE",
    "requested_state": "AUTONOMOUS"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:31.290+05:30"
}
```

Use `ERROR` for protocol-level or processing errors where a normal action response cannot be formed. Use a `RESPONSE` with `status: REJECTED` when the request was understood but policy or action validation refused it.

### 7.6 Correlation rules

- Every response must set `correlation_id` to the request's `message_id`.
- Events generated as a consequence of a request may use the same correlation ID if they are directly related.
- Independent events use `correlation_id: null`.
- A response must not change the original request's `message_id`.
- The receiver must reject or log responses whose correlation ID does not match a pending request, according to the component's role and policy.

## 8. Validation rules

Validation must happen in layers. Do not dispatch a partially validated message.

### 8.1 Transport validation

Before JSON parsing:

- Read exactly four bytes for the length prefix.
- Interpret it as an unsigned big-endian integer.
- Reject zero-length frames.
- Reject frames larger than the configured maximum.
- Read exactly the declared number of bytes.
- Treat premature EOF as a disconnected or malformed peer.
- Do not allocate unbounded memory based on an untrusted length.

Recommended initial maximum frame size: **64 KiB**. Most Rithum control messages should be far smaller. Large image, video, or audio data must not be sent through this control protocol; use a separate bounded data path if such transfer is ever required.

### 8.2 JSON validation

- Decode as UTF-8.
- Require one JSON object per frame.
- Reject malformed JSON.
- Reject duplicate object keys where the parser supports duplicate-key detection.
- Reject non-standard JSON constants such as NaN and Infinity.
- Reject trailing data after the JSON object.
- Enforce nesting and size limits where practical.

### 8.3 Envelope validation

Validate:

- Exact required top-level fields.
- Correct field types.
- Supported `protocol_version`.
- Valid UUID format for `message_id` (and `correlation_id` when non-null).
- Positive integer `sequence`; booleans must not be accepted as integers.
- Registered `source` and valid `target`.
- Known `message_type`.
- Non-empty, registered `action`.
- Object types for `payload` and `metadata`.
- Valid ISO 8601 timestamp with an explicit offset.

### 8.4 Timestamp validation

The Raspberry Pi is the authoritative clock for internal IPC timestamps.

Rules:

- The supervisor stamps messages it creates.
- A worker creating a message obtains the timestamp from the Pi's local system clock.
- A browser/client timestamp is untrusted and must not be copied into the authoritative `timestamp` field.
- Use an ISO 8601 string with milliseconds and an explicit UTC offset, for example `2026-11-22T18:40:31.245+05:30`.
- The intended Pi timezone is `Asia/Kolkata`; the timestamp must reflect the Pi's actual configured local timezone.
- Do not hardcode `+05:30` in code. Read the system timezone dynamically.
- Do not use wall-clock timestamps for heartbeat expiry, dead-man timeouts, or command deadlines. Use a monotonic clock.
- Clock synchronization status should be monitored separately. A wall-clock jump must not invalidate monotonic safety timers.

A timestamp supplied by a worker is useful for diagnostics, but the supervisor should record its own receive time as a separate internal log field. If a future schema needs both values on the wire, add a documented field such as `received_timestamp`; do not silently overload `timestamp`.

### 8.5 Source authentication and authorization

Unix socket filesystem permissions are the first access-control layer, not the entire authorization model.

The supervisor should:

- Create the socket in a directory not writable by untrusted users.
- Set restrictive directory and socket permissions.
- Verify peer credentials where supported by the platform.
- Map the connected peer to an allowed component identity.
- Ensure the claimed `source` matches the authenticated peer identity.
- Apply an action allowlist for that source.
- Reject attempts to impersonate `supervisor`.
- Keep web user authentication and operator authorization separate from local process identity.

A JSON field claiming `"source": "supervisor"` is not proof that the sender is the supervisor.

### 8.6 Action and payload validation

For each action:

- Verify that the action is permitted for the selected `message_type`.
- Verify the source is permitted to send it.
- Verify the target is valid for that action.
- Validate required payload keys and types.
- Reject missing required fields.
- Reject unknown fields unless the action schema explicitly permits them.
- Validate numeric bounds and units.
- Validate operating-state and safety preconditions.
- Reject unsupported or not-yet-implemented actions.

### 8.7 Safety validation

For any motion-related request, the supervisor must check at minimum:

- System startup/self-test has completed.
- No latched fault or emergency-stop condition blocks operation.
- Motor hardware is initialized and explicitly enabled through the safety-controlled path.
- Requested operating state permits motion.
- A valid operator lease exists for manual operation.
- Dead-man/command heartbeat is current.
- Command values are within configured limits.
- Required hardware interlocks are satisfied.
- The request has not expired.

Before the later IR integration phase, autonomous movement must remain unavailable. After IR integration, obstacle policy must be applied to manual movement as well as autonomous movement where the safety design requires it.

A software protocol is not a substitute for a physical emergency-stop circuit or appropriate electrical protection.

### 8.8 Sequence and replay handling

- Sequence numbers increase per sender process session.
- A receiver should detect duplicate or stale sequence values.
- Sequence gaps may be logged; they are not automatically fatal for every event stream.
- Commands must not be executed twice because a sender retries after a lost response.
- Use idempotency keys or a bounded recent-message cache for actions where duplicate execution could cause harm.
- For non-idempotent actions, do not automatically retry after an uncertain outcome. Query status or require operator intervention.

A process restart begins a new sequence session. A future protocol revision may add `sender_session_id` to make this explicit on the wire.

### 8.9 Timeout validation

- `timeout_ms` must be a positive bounded integer when present.
- The supervisor applies a configured maximum and may shorten a requested timeout.
- Timeouts are measured using a monotonic clock.
- On expiry, the supervisor marks the request timed out and stops waiting for its result.
- A timeout does not prove that the underlying worker did nothing. For operations with side effects, reconcile actual state before retrying.
- For manual movement, the independent dead-man mechanism must stop motion on lease/heartbeat expiry regardless of whether an IPC response arrives.

### 8.10 Error handling

Errors should be machine-readable and stable. Recommended codes:

| Error code | Meaning |
|---|---|
| `MALFORMED_FRAME` | Invalid or incomplete transport frame. |
| `MESSAGE_TOO_LARGE` | Frame exceeds configured maximum. |
| `MALFORMED_JSON` | Payload is not valid JSON. |
| `INVALID_ENVELOPE` | Required fields or field types are invalid. |
| `UNSUPPORTED_PROTOCOL_VERSION` | Receiver does not support the version. |
| `UNKNOWN_SOURCE` | Sender identity is not registered. |
| `UNKNOWN_TARGET` | Recipient is not registered. |
| `UNKNOWN_MESSAGE_TYPE` | Message type is not supported. |
| `UNKNOWN_ACTION` | Action is not registered. |
| `INVALID_PAYLOAD` | Action payload does not match its schema. |
| `UNAUTHORIZED_ACTION` | Sender is not permitted to request the action. |
| `PEER_IDENTITY_MISMATCH` | Claimed source does not match socket peer. |
| `SEQUENCE_REPLAY` | Duplicate or stale message detected. |
| `REQUEST_TIMEOUT` | Request exceeded its deadline. |
| `INVALID_STATE_TRANSITION` | Requested state change is not allowed. |
| `SAFETY_INTERLOCK_ACTIVE` | Safety condition blocks operation. |
| `OPERATOR_LEASE_REQUIRED` | No valid operator lease exists. |
| `AUTONOMY_NOT_ENABLED` | Autonomous mode is disabled or unavailable. |
| `WORKER_UNAVAILABLE` | Required worker is not ready. |
| `INTERNAL_ERROR` | Unexpected internal processing failure. |

Do not expose stack traces, secrets, filesystem paths, or sensitive internal details to remote clients. Detailed exceptions belong in protected local logs.

## 9. Timestamp and timekeeping standard

### 9.1 Required representation

Use:

```text
YYYY-MM-DDTHH:MM:SS.mmm±HH:MM
```

Example for the intended India timezone:

```text
2026-11-22T18:40:31.245+05:30
```

### 9.2 Python implementation

Use the Pi's configured local timezone dynamically:

```python
from datetime import datetime

def local_timestamp() -> str:
    return datetime.now().astimezone().isoformat(
        timespec="milliseconds"
    )
```

Do not use:

```python
datetime.utcnow()
```

for this protocol's local timestamp field. It returns a naive UTC datetime in older Python patterns and does not express the Pi's local timezone.

### 9.3 Wall clock versus monotonic clock

| Use case | Clock |
|---|---|
| Human-readable message timestamp | Local wall clock with offset |
| Audit log timestamp | Local wall clock with offset |
| Heartbeat expiry | Monotonic clock |
| Dead-man timeout | Monotonic clock |
| Command execution deadline | Monotonic clock |
| Measuring worker duration | Monotonic clock |

The Pi's system clock should be synchronized using the operating system's configured time service. The protocol itself does not synchronize clocks.

## 10. Transport framing over Unix Domain Sockets

### 10.1 Frame layout

Each message is transmitted as:

```text
+---------------------------+---------------------------+
| 4-byte unsigned length    | UTF-8 JSON message bytes  |
| big-endian                | exactly N bytes           |
+---------------------------+---------------------------+
```

The length prefix contains the number of JSON bytes, not the number of characters.

### 10.2 Sending

The sender must:

1. Serialize the complete envelope to compact UTF-8 JSON.
2. Calculate the byte length.
3. Reject the message if it exceeds the configured maximum.
4. Prefix the JSON bytes with a four-byte big-endian length.
5. Send the complete frame, handling partial writes.

### 10.3 Receiving

The receiver must:

1. Read exactly four bytes.
2. Decode the length.
3. Validate the length before allocating the payload buffer.
4. Read exactly that many bytes.
5. Decode UTF-8.
6. Parse and validate JSON.
7. Dispatch only after all validation layers succeed.

### 10.4 Connection behavior

- A socket connection is not proof of authorization.
- A peer disconnect must be handled without crashing the supervisor.
- Partial frames must be discarded on connection termination.
- Per-client buffers and pending requests must be bounded.
- A malformed client must not block other clients indefinitely.
- The supervisor should apply read/write deadlines and connection limits.
- Local socket paths and permissions must be controlled by the supervisor.

### 10.5 Data that must not use this protocol

Do not send camera frames, video, audio streams, large model outputs, or other bulk binary data through the control IPC channel. Keep the control plane small. If bulk data is required later, define a separate data transport and lifecycle.

## 11. Logging and observability

Every received or generated message should be traceable through structured logs.

Recommended log fields:

```text
timestamp
level
component
message_id
correlation_id
sequence
source
target
message_type
action
result
duration_ms
error_code
```

Logging rules:

- Log command receipt, validation result, authorization result, and final outcome.
- Log state transitions with previous state, new state, and reason.
- Log worker start, stop, crash, restart, and heartbeat expiry.
- Log malformed or unauthorized messages with enough context to diagnose them.
- Do not log passwords, tokens, cookies, private keys, or sensitive personal data.
- Avoid logging every high-frequency movement update at INFO level; use DEBUG or sampled telemetry.
- Use the same message and correlation IDs across supervisor and worker logs.
- Keep logs bounded and rotate them.

## 12. Security considerations

- UDS is local IPC, not a substitute for application authentication.
- Use restrictive socket directory permissions.
- Authenticate peer processes using operating-system peer credentials where available.
- Validate the claimed source against the peer identity.
- Use per-component action allowlists.
- Do not allow arbitrary process names, arbitrary filesystem paths, shell commands, or Python module names in payloads.
- Do not expose the IPC socket over TCP or the public internet.
- Remote clients communicate through the authenticated web service, not directly through UDS.
- Treat all data from web, voice, and vision boundaries as untrusted until validated.
- Keep secrets out of JSON messages and logs.
- Rate-limit command sources and bound all queues.
- Apply motion safety checks independently of transport priority.

## 13. Versioning and compatibility

The current protocol version is `1.0`.

For version 1.0:

- `protocol_version` is required.
- Unknown top-level fields are rejected.
- Unknown message types and actions are rejected.
- Payload schemas are strict by default.
- A receiver must not silently reinterpret an unsupported version.

Changes that add optional metadata or actions may be compatible only if explicitly documented and implemented with compatible validation. Changes to required fields, field meanings, framing, or response semantics require a protocol version change.

Do not assume that a process running an older version can safely communicate with a newer process. The supervisor should check protocol compatibility during connection setup or the first exchange and reject incompatible peers clearly.

## 14. Recommended implementation constants

These are initial engineering defaults, not immutable protocol guarantees. They should be configurable and revisited after measurement.

| Setting | Initial value | Notes |
|---|---:|---|
| Protocol version | `1.0` | Explicit version in every message. |
| Maximum frame size | 65,536 bytes | Control messages only. |
| Default command timeout | 2,000 ms | Action-specific overrides may be needed. |
| Maximum command timeout | 30,000 ms | Supervisor clamps requested values. |
| Heartbeat interval | 1,000 ms | Per-worker tuning may differ. |
| Heartbeat timeout | 3,000 ms | Use monotonic time; tune per worker. |
| Sequence start | 1 | Resets on process session restart. |
| Socket permissions | `0600` | Adjust only if group-based access is deliberately configured. |
| Socket directory permissions | `0700` | Restrict directory traversal/access. |

The manual movement dead-man timeout is a separate safety setting. The existing Rithum design has a target initial dead-man timeout of approximately 400 ms; it must be independently enforced and tested. Do not replace it with the general IPC heartbeat timeout.

## 15. Example messages

### 15.1 Request manual local control

```json
{
  "protocol_version": "1.0",
  "message_id": "request-uuid",
  "correlation_id": null,
  "sequence": 1,
  "source": "web_controller",
  "target": "supervisor",
  "message_type": "COMMAND",
  "action": "SET_OPERATING_STATE",
  "payload": {
    "state": "MANUAL_LOCAL"
  },
  "metadata": {
    "priority": "NORMAL",
    "requires_response": true,
    "timeout_ms": 2000
  },
  "timestamp": "2026-11-22T18:40:31.245+05:30"
}
```

This request is not automatically accepted. The supervisor checks the current state, authorization, local/remote mode policy, and safety conditions.

### 15.2 Accept a request

```json
{
  "protocol_version": "1.0",
  "message_id": "response-uuid",
  "correlation_id": "request-uuid",
  "sequence": 2,
  "source": "supervisor",
  "target": "web_controller",
  "message_type": "RESPONSE",
  "action": "SET_OPERATING_STATE",
  "payload": {
    "status": "ACCEPTED",
    "requested_state": "MANUAL_LOCAL"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:31.260+05:30"
}
```

### 15.3 Report a state transition

```json
{
  "protocol_version": "1.0",
  "message_id": "event-uuid",
  "correlation_id": "request-uuid",
  "sequence": 3,
  "source": "supervisor",
  "target": "broadcast",
  "message_type": "EVENT",
  "action": "STATE_CHANGED",
  "payload": {
    "previous_state": "IDLE",
    "current_state": "MANUAL_LOCAL",
    "reason": "Authorized local operator request"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:31.275+05:30"
}
```

### 15.4 Reject autonomous mode before IR integration

```json
{
  "protocol_version": "1.0",
  "message_id": "response-uuid",
  "correlation_id": "request-uuid",
  "sequence": 4,
  "source": "supervisor",
  "target": "web_controller",
  "message_type": "RESPONSE",
  "action": "SET_OPERATING_STATE",
  "payload": {
    "status": "REJECTED",
    "error_code": "AUTONOMY_NOT_ENABLED",
    "message": "Autonomous operation is not enabled in this build.",
    "current_state": "IDLE",
    "requested_state": "AUTONOMOUS"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:31.280+05:30"
}
```

### 15.5 Worker heartbeat

```json
{
  "protocol_version": "1.0",
  "message_id": "heartbeat-uuid",
  "correlation_id": null,
  "sequence": 28,
  "source": "vision_worker",
  "target": "supervisor",
  "message_type": "HEARTBEAT",
  "action": "WORKER_HEALTH",
  "payload": {
    "status": "HEALTHY",
    "uptime_ms": 125000,
    "load_state": "NORMAL"
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:32.000+05:30"
}
```

### 15.6 Human detected

```json
{
  "protocol_version": "1.0",
  "message_id": "event-uuid",
  "correlation_id": null,
  "sequence": 29,
  "source": "vision_worker",
  "target": "supervisor",
  "message_type": "EVENT",
  "action": "HUMAN_DETECTED",
  "payload": {
    "confidence": 0.94,
    "frame_width": 640,
    "frame_height": 480
  },
  "metadata": {},
  "timestamp": "2026-11-22T18:40:32.150+05:30"
}
```

The event reports an observation only. It does not authorize a state transition or movement.

## 16. Implementation checklist

Before the protocol is considered implemented, the following must be completed:

### Schema and validation
- [ ] Define a single canonical message model in code.
- [ ] Validate required fields and strict types.
- [ ] Validate UUIDs, sequence numbers, source, target, type, and action.
- [ ] Validate action-specific payload schemas.
- [ ] Validate timestamp format and explicit offset.
- [ ] Enforce frame and payload size limits.
- [ ] Reject malformed JSON and duplicate keys.

### Transport
- [ ] Implement four-byte big-endian length framing.
- [ ] Handle partial reads and writes.
- [ ] Handle disconnects and incomplete frames.
- [ ] Apply connection and queue limits.
- [ ] Set restrictive socket and directory permissions.

### Authorization and safety
- [ ] Verify UDS peer identity where supported.
- [ ] Match peer identity to `source`.
- [ ] Enforce per-component action allowlists.
- [ ] Reject direct worker lifecycle requests from ordinary workers.
- [ ] Keep state transitions supervisor-controlled.
- [ ] Keep all movement disabled by default.
- [ ] Enforce operator lease and dead-man checks before manual motion.
- [ ] Keep autonomy disabled until its later implementation phase.

### Response lifecycle
- [ ] Implement correlated responses.
- [ ] Distinguish accepted from completed.
- [ ] Track pending asynchronous requests.
- [ ] Expire pending requests using monotonic time.
- [ ] Handle duplicate/retried commands safely.
- [ ] Return stable error codes.

### Testing
- [ ] Unit-test schema validation.
- [ ] Unit-test action authorization.
- [ ] Test invalid and oversized frames.
- [ ] Test partial socket reads and writes.
- [ ] Test disconnects during frame transfer.
- [ ] Test duplicate IDs and sequence replay.
- [ ] Test correlation ID matching.
- [ ] Test request timeout behavior.
- [ ] Test that invalid or unauthorized motion commands never reach hardware.
- [ ] Test that E-stop and fault paths cannot be bypassed.

## 17. Decisions still requiring implementation-level confirmation

This document deliberately leaves some details to be finalized during implementation:

1. Whether each worker uses one persistent socket connection or reconnects per request.
2. Whether event delivery uses per-worker sockets, a supervisor event broker, or both.
3. Whether `sender_session_id` is added in protocol version 1.1.
4. Exact action-specific schemas for `MOVE`, diagnostics, and face animation.
5. Exact peer-credential API and socket ownership on the deployed Ubuntu kernel/userspace.
6. Whether the web controller talks to the supervisor through a dedicated web-manager worker or a direct supervisor IPC client.

These decisions must be recorded before the relevant feature is implemented. They must not be guessed independently by different workers.

---

**End of protocol specification.**
