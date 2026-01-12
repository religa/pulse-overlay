"""Tests for pulse_server.config module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from pulse_server.config import (
    BLEConfig,
    Config,
    DeviceConfig,
    ServerConfig,
    _parse_config,
    load_config,
)


class TestServerConfig:
    """Tests for ServerConfig dataclass."""

    def test_default_values(self):
        """ServerConfig has correct defaults."""
        config = ServerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8765
        assert config.broadcast_timeout == 0.5
        assert config.log_level == "INFO"

    def test_custom_values(self):
        """ServerConfig accepts custom values."""
        config = ServerConfig(
            host="0.0.0.0",
            port=9000,
            broadcast_timeout=1.5,
            log_level="DEBUG",
        )
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.broadcast_timeout == 1.5
        assert config.log_level == "DEBUG"


class TestBLEConfig:
    """Tests for BLEConfig dataclass."""

    def test_default_values(self):
        """BLEConfig has correct defaults."""
        config = BLEConfig()
        assert config.scan_timeout == 5.0
        assert config.reconnect_min == 1.0
        assert config.reconnect_max == 30.0

    def test_custom_values(self):
        """BLEConfig accepts custom values."""
        config = BLEConfig(
            scan_timeout=10.0,
            reconnect_min=2.0,
            reconnect_max=60.0,
        )
        assert config.scan_timeout == 10.0
        assert config.reconnect_min == 2.0
        assert config.reconnect_max == 60.0


class TestDeviceConfig:
    """Tests for DeviceConfig dataclass."""

    def test_default_values(self):
        """DeviceConfig has correct defaults."""
        config = DeviceConfig()
        assert config.address == ""
        assert config.name_filter == ""

    def test_custom_values(self):
        """DeviceConfig accepts custom values."""
        config = DeviceConfig(
            address="AA:BB:CC:DD:EE:FF",
            name_filter="Polar",
        )
        assert config.address == "AA:BB:CC:DD:EE:FF"
        assert config.name_filter == "Polar"


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Config has correct nested defaults."""
        config = Config()
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.ble, BLEConfig)
        assert isinstance(config.device, DeviceConfig)
        assert config.server.host == "127.0.0.1"
        assert config.ble.scan_timeout == 5.0
        assert config.device.address == ""

    def test_custom_nested_configs(self):
        """Config accepts custom nested configs."""
        config = Config(
            server=ServerConfig(port=9000),
            ble=BLEConfig(scan_timeout=10.0),
            device=DeviceConfig(address="11:22:33:44:55:66"),
        )
        assert config.server.port == 9000
        assert config.ble.scan_timeout == 10.0
        assert config.device.address == "11:22:33:44:55:66"


class TestParseConfig:
    """Tests for _parse_config function."""

    def test_parse_full_config(self, sample_config_dict):
        """Parse complete config dict."""
        config = _parse_config(sample_config_dict)
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9000
        assert config.server.broadcast_timeout == 1.0
        assert config.server.log_level == "DEBUG"
        assert config.ble.scan_timeout == 10.0
        assert config.ble.reconnect_min == 2.0
        assert config.ble.reconnect_max == 60.0
        assert config.device.address == "11:22:33:44:55:66"
        assert config.device.name_filter == "Polar"

    def test_parse_empty_config(self):
        """Parse empty dict uses all defaults."""
        config = _parse_config({})
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8765
        assert config.ble.scan_timeout == 5.0
        assert config.device.address == ""

    def test_parse_partial_config(self, partial_config_dict):
        """Parse partial config fills in defaults."""
        config = _parse_config(partial_config_dict)
        # Specified values
        assert config.server.port == 8080
        assert config.ble.scan_timeout == 3.0
        # Default values
        assert config.server.host == "127.0.0.1"
        assert config.server.log_level == "INFO"
        assert config.ble.reconnect_min == 1.0
        assert config.device.address == ""

    def test_parse_server_section_only(self):
        """Parse config with only server section."""
        data = {"server": {"host": "192.168.1.1", "port": 8080}}
        config = _parse_config(data)
        assert config.server.host == "192.168.1.1"
        assert config.server.port == 8080
        # Other sections use defaults
        assert config.ble.scan_timeout == 5.0
        assert config.device.address == ""

    def test_parse_ble_section_only(self):
        """Parse config with only ble section."""
        data = {"ble": {"scan_timeout": 15.0, "reconnect_max": 120.0}}
        config = _parse_config(data)
        assert config.ble.scan_timeout == 15.0
        assert config.ble.reconnect_max == 120.0
        # Other sections use defaults
        assert config.server.port == 8765
        assert config.device.address == ""

    def test_parse_device_section_only(self):
        """Parse config with only device section."""
        data = {"device": {"address": "AA:BB:CC:DD:EE:FF"}}
        config = _parse_config(data)
        assert config.device.address == "AA:BB:CC:DD:EE:FF"
        assert config.device.name_filter == ""
        # Other sections use defaults
        assert config.server.port == 8765
        assert config.ble.scan_timeout == 5.0

    def test_parse_unknown_keys_raises_error(self):
        """Unknown keys in config sections raise TypeError."""
        data = {
            "server": {"host": "0.0.0.0", "unknown_key": "value"},
        }
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            _parse_config(data)

    def test_parse_unknown_section_ignored(self):
        """Unknown top-level sections are ignored."""
        data = {
            "server": {"host": "0.0.0.0"},
            "unknown_section": {"key": "value"},
        }
        config = _parse_config(data)
        assert config.server.host == "0.0.0.0"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_no_files_exist(self, tmp_path, monkeypatch):
        """load_config returns defaults when no config file exists."""
        # Change to temp dir with no config file
        monkeypatch.chdir(tmp_path)
        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = load_config()
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 8765

    def test_load_config_from_local_file(self, tmp_path, monkeypatch):
        """load_config reads from ./config.toml first."""
        monkeypatch.chdir(tmp_path)
        config_content = b"""
[server]
host = "0.0.0.0"
port = 9999
"""
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(config_content)

        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = load_config()
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 9999

    def test_load_config_from_home_dir(self, tmp_path, monkeypatch):
        """load_config reads from ~/.config/pulse-server/config.toml."""
        monkeypatch.chdir(tmp_path)

        # Create home config directory
        home_config_dir = tmp_path / "home" / ".config" / "pulse-server"
        home_config_dir.mkdir(parents=True)
        config_file = home_config_dir / "config.toml"
        config_file.write_bytes(b"""
[server]
port = 7777

[ble]
scan_timeout = 20.0
""")

        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = load_config()
        assert config.server.port == 7777
        assert config.ble.scan_timeout == 20.0

    def test_load_config_local_takes_priority(self, tmp_path, monkeypatch):
        """Local config.toml takes priority over home config."""
        monkeypatch.chdir(tmp_path)

        # Create local config
        local_config = tmp_path / "config.toml"
        local_config.write_bytes(b"""
[server]
port = 1111
""")

        # Create home config
        home_config_dir = tmp_path / "home" / ".config" / "pulse-server"
        home_config_dir.mkdir(parents=True)
        home_config = home_config_dir / "config.toml"
        home_config.write_bytes(b"""
[server]
port = 2222
""")

        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = load_config()
        # Local config wins
        assert config.server.port == 1111

    def test_load_config_full_file(self, tmp_path, monkeypatch):
        """load_config parses complete TOML file."""
        monkeypatch.chdir(tmp_path)
        config_content = b"""
[server]
host = "192.168.1.100"
port = 8000
broadcast_timeout = 2.0
log_level = "DEBUG"

[ble]
scan_timeout = 10.0
reconnect_min = 0.5
reconnect_max = 45.0

[device]
address = "AA:BB:CC:DD:EE:FF"
name_filter = "Polar H10"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_bytes(config_content)

        with patch.object(Path, "home", return_value=tmp_path / "home"):
            config = load_config()

        assert config.server.host == "192.168.1.100"
        assert config.server.port == 8000
        assert config.server.broadcast_timeout == 2.0
        assert config.server.log_level == "DEBUG"
        assert config.ble.scan_timeout == 10.0
        assert config.ble.reconnect_min == 0.5
        assert config.ble.reconnect_max == 45.0
        assert config.device.address == "AA:BB:CC:DD:EE:FF"
        assert config.device.name_filter == "Polar H10"
