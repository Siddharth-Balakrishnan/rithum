"""Centralized configuration for Rithum."""

from dataclasses import dataclass, fields
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value for {name}: {value!r}")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer value for {name}: {value!r}"
        ) from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for {name}: {value!r}"
        ) from exc


@dataclass(frozen=True, slots=True)
class RobotConfig:
    name: str = "Rithum"
    hostname: str = "r1t-hum"
    version: str = "0.1.0"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    environment: str = "development"
    log_level: str = "INFO"
    log_history_limit: int = 1000
    face_enabled: bool = True
    face_fps: int = 30


@dataclass(frozen=True, slots=True)
class HardwareConfig:
    platform: str = "raspberry_pi_5"
    gpio_backend: str = "gpiod_v2"

    motor_pins: tuple[int, ...] = ()
    ir_sensor_pins: tuple[int, ...] = ()
    encoder_pins: tuple[int, ...] = ()

    motors_enabled: bool = False
    ir_sensors_enabled: bool = False
    encoders_enabled: bool = False


@dataclass(frozen=True, slots=True)
class SafetyConfig:
    autonomy_enabled: bool = False
    deadman_timeout_seconds: float = 0.4
    motors_disabled_at_boot: bool = True
    operator_heartbeat_timeout_seconds: float = 1.0


@dataclass(frozen=True, slots=True)
class NetworkConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    websocket_enabled: bool = True
    authentication_required: bool = True


@dataclass(frozen=True, slots=True)
class AppConfig:
    robot: RobotConfig
    runtime: RuntimeConfig
    hardware: HardwareConfig
    safety: SafetyConfig
    network: NetworkConfig


def load_config() -> AppConfig:
    """Load application configuration from environment variables."""

    config = AppConfig(
        robot=RobotConfig(
            name=os.getenv("RITHUM_NAME", "Rithum"),
            hostname=os.getenv("RITHUM_HOSTNAME", "r1t-hum"),
            version=os.getenv("RITHUM_VERSION", "0.1.0"),
        ),

        runtime=RuntimeConfig(
            environment=os.getenv(
                "RITHUM_ENVIRONMENT", "development"
            ),
            log_level=os.getenv("RITHUM_LOG_LEVEL", "INFO").upper(),
            log_history_limit=_env_int(
                "RITHUM_LOG_HISTORY_LIMIT", 1000
            ),
            face_enabled=_env_bool(
                "RITHUM_FACE_ENABLED", True
            ),
            face_fps=_env_int("RITHUM_FACE_FPS", 30),
        ),

        hardware=HardwareConfig(
            platform="raspberry_pi_5",
            gpio_backend="gpiod_v2",
            motors_enabled=_env_bool(
                "RITHUM_MOTORS_ENABLED", False
            ),
            ir_sensors_enabled=_env_bool(
                "RITHUM_IR_ENABLED", False
            ),
            encoders_enabled=_env_bool(
                "RITHUM_ENCODERS_ENABLED", False
            ),
        ),

        safety=SafetyConfig(
            autonomy_enabled=_env_bool(
                "RITHUM_AUTONOMY_ENABLED", False
            ),
            deadman_timeout_seconds=_env_float(
                "RITHUM_DEADMAN_TIMEOUT", 0.4
            ),
            motors_disabled_at_boot=_env_bool(
                "RITHUM_MOTORS_DISABLED_AT_BOOT", True
            ),
            operator_heartbeat_timeout_seconds=_env_float(
                "RITHUM_OPERATOR_HEARTBEAT_TIMEOUT", 1.0
            ),
        ),

        network=NetworkConfig(
            host=os.getenv("RITHUM_WEB_HOST", "127.0.0.1"),
            port=_env_int("RITHUM_WEB_PORT", 8765),
            websocket_enabled=_env_bool(
                "RITHUM_WEBSOCKET_ENABLED", True
            ),
            authentication_required=_env_bool(
                "RITHUM_AUTH_REQUIRED", True
            ),
        ),
    )

    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    """Validate configuration and reject unsafe or invalid settings."""

    if not config.robot.name.strip():
        raise ValueError("Robot name cannot be empty.")

    valid_log_levels = {
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
    }

    if config.runtime.log_level not in valid_log_levels:
        raise ValueError(
            f"Invalid log level: {config.runtime.log_level}"
        )

    if config.runtime.log_history_limit < 1:
        raise ValueError("Log history limit must be positive.")

    if not 1 <= config.runtime.face_fps <= 120:
        raise ValueError("Face FPS must be between 1 and 120.")

    if not 1 <= config.network.port <= 65535:
        raise ValueError("Network port must be between 1 and 65535.")

    if config.safety.deadman_timeout_seconds <= 0:
        raise ValueError("Deadman timeout must be positive.")

    if config.safety.operator_heartbeat_timeout_seconds <= 0:
        raise ValueError("Operator heartbeat timeout must be positive.")

    if config.safety.autonomy_enabled and not config.hardware.ir_sensors_enabled:
        raise ValueError(
            "Autonomy cannot be enabled while IR sensors are disabled."
        )

    if not config.safety.motors_disabled_at_boot:
        raise ValueError(
            "Motor outputs must remain disabled during boot."
        )


def print_config(config: AppConfig) -> None:
    """Print configuration in a readable, section-based layout."""

    sections = (
        ("ROBOT", config.robot),
        ("RUNTIME", config.runtime),
        ("HARDWARE", config.hardware),
        ("SAFETY", config.safety),
        ("NETWORK", config.network),
    )

    print("\nRITHUM CONFIGURATION")
    print("=" * 52)

    for section_name, section in sections:
        print(f"\n{section_name}")
        print("-" * 52)

        for item in fields(section):
            key = item.name.replace("_", " ").title()
            value = getattr(section, item.name)

            print(f"{key:<38} {value}")

        print()


if __name__ == "__main__":
    print_config(load_config())
