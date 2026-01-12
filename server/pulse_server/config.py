"""Configuration file loading and defaults."""

import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    broadcast_timeout: float = 0.5
    log_level: str = "INFO"


@dataclass
class BLEConfig:
    scan_timeout: float = 5.0
    reconnect_min: float = 1.0
    reconnect_max: float = 30.0


@dataclass
class DeviceConfig:
    address: str = ""
    name_filter: str = ""


@dataclass
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    ble: BLEConfig = field(default_factory=BLEConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)


def load_config() -> Config:
    """Load config from file, with defaults for missing values."""
    paths = [
        Path("./config.toml"),
        Path.home() / ".config" / "pulse-server" / "config.toml",
    ]

    for path in paths:
        if path.exists():
            try:
                with open(path, "rb") as f:
                    data = tomllib.load(f)
                return _parse_config(data)
            except tomllib.TOMLDecodeError as e:
                logger.warning("Failed to parse config '%s': %s. Using defaults.", path, e)
                return Config()

    return Config()


def _parse_config(data: dict) -> Config:
    """Parse TOML dict into Config dataclass.

    Uses dataclass defaults for missing values.
    """
    return Config(
        server=ServerConfig(**data.get("server", {})),
        ble=BLEConfig(**data.get("ble", {})),
        device=DeviceConfig(**data.get("device", {})),
    )
