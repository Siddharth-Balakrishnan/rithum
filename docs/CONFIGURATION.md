# Configuration

## 1. Source of truth

The current configuration implementation is `core/config.py`. It groups settings into dataclass sections and loads supported values from environment variables. `load_config()` builds and validates an `AppConfig`; `print_config()` prints the sections in a readable format.

Do not assume a `.env` file is loaded automatically. The presence of `.env` in `.gitignore` only prevents accidental commits; it does not implement dotenv loading.

## 2. Configuration sections

The current model contains:

| Section | Purpose |
|---|---|
| `RobotConfig` | Robot identity and software version. |
| `RuntimeConfig` | Environment, logging, and face-renderer runtime defaults. |
| `HardwareConfig` | Platform, GPIO backend, pin mappings, and feature availability flags. |
| `SafetyConfig` | Autonomy gate, dead-man timeout, boot motor-disable policy, and operator heartbeat timeout. |
| `NetworkConfig` | Web bind address, port, WebSocket flag, and authentication requirement. |

## 3. Environment variables

The following names are present in the current configuration implementation:

| Variable | Meaning | Recorded default / behavior |
|---|---|---|
| `RITHUM_NAME` | Robot display name | `Rithum` |
| `RITHUM_HOSTNAME` | Robot hostname label | `r1t-hum` |
| `RITHUM_VERSION` | Project version | `0.1.0` |
| `RITHUM_ENVIRONMENT` | Runtime environment | `development` |
| `RITHUM_LOG_LEVEL` | Logging threshold | `INFO` |
| `RITHUM_LOG_HISTORY_LIMIT` | In-memory history limit | `1000` |
| `RITHUM_FACE_ENABLED` | Face subsystem enabled flag | `true` |
| `RITHUM_FACE_FPS` | Face target frame rate | `30` |
| `RITHUM_MOTORS_ENABLED` | Motor integration availability flag | `false` |
| `RITHUM_IR_ENABLED` | IR sensor integration availability flag | `false` |
| `RITHUM_ENCODERS_ENABLED` | Encoder integration availability flag | `false` |
| `RITHUM_AUTONOMY_ENABLED` | Autonomous mode configuration gate | `false` |
| `RITHUM_DEADMAN_TIMEOUT` | Motion dead-man timeout in seconds | `0.4` |
| `RITHUM_MOTORS_DISABLED_AT_BOOT` | Require motor outputs disabled at boot | `true`; validation rejects `false` |
| `RITHUM_OPERATOR_HEARTBEAT_TIMEOUT` | Operator heartbeat timeout in seconds | `1.0` |
| `RITHUM_WEB_HOST` | Web bind address | `127.0.0.1` |
| `RITHUM_WEB_PORT` | Web service port | `8765` |
| `RITHUM_WEBSOCKET_ENABLED` | WebSocket feature flag | `true` |
| `RITHUM_AUTH_REQUIRED` | Require application authentication | `true` |

The defaults above should be checked against `core/config.py` after code changes. The code is authoritative.

## 4. Validation rules

The current validator checks:

- robot name is not empty;
- log level is one of the supported logging levels;
- log history limit is positive;
- face FPS is within 1–120;
- web port is within 1–65535;
- dead-man timeout is positive;
- operator heartbeat timeout is positive;
- autonomy cannot be enabled while IR sensors are disabled;
- motor outputs must remain disabled at boot.

These checks validate configuration values. They do not prove that hardware is wired correctly or that the selected sensors are safe for Pi GPIO.

## 5. Inspect effective configuration

Activate the virtual environment, then run:

```bash
python -m core.config
```

This prints the loaded configuration. Review it before starting any future hardware service.

To inspect a specific environment override without permanently changing the shell:

```bash
RITHUM_LOG_LEVEL=DEBUG python -m core.config
```

For a Boolean example:

```bash
RITHUM_FACE_ENABLED=false python -m core.config
```

Environment variables set in a shell affect child processes launched from that shell. They do not automatically modify an already-running systemd service.

## 6. Safe configuration examples

Development should remain conservative:

```bash
export RITHUM_ENVIRONMENT=development
export RITHUM_LOG_LEVEL=DEBUG
export RITHUM_WEB_HOST=127.0.0.1
export RITHUM_WEB_PORT=8765
export RITHUM_MOTORS_DISABLED_AT_BOOT=true
export RITHUM_AUTONOMY_ENABLED=false
export RITHUM_IR_ENABLED=false
```

Do not set autonomy true before the IR phase is complete. Do not set a motor-related flag expecting it to make physical outputs safe; hardware output enable must be separately controlled by the supervisor and safety layer.

## 7. Configuration debugging

If configuration loading fails:

1. Run `python -m core.config`.
2. Read the full exception.
3. Print only the relevant environment variable, not all secrets:
   `printf '%s\n' "$RITHUM_WEB_PORT"`.
4. Check Boolean spelling and numeric parsing.
5. Confirm that the process is using the expected virtual environment.
6. Confirm systemd unit environment overrides if the process is service-managed.
7. Add/adjust a unit test for the new setting.

Avoid dumping the complete process environment into logs because it may contain credentials or tokens.
