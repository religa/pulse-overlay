"""Tests for pulse_server.__main__ module."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

from pulse_server.__main__ import main, run
from pulse_server.config import BLEConfig, Config, ServerConfig


class TestMainArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_default_arguments(self):
        """main() uses config defaults when no args provided."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server"]):
                        main()

    def test_host_argument(self):
        """--host argument overrides config."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-H", "0.0.0.0"]):
                        main()

    def test_port_argument(self):
        """--port argument overrides config."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-p", "9000"]):
                        main()

    def test_device_argument(self):
        """-d/--device argument sets device address."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-d", "AA:BB:CC:DD:EE:FF"]):
                        main()

    def test_name_filter_argument(self):
        """-n/--name argument sets name filter."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-n", "Polar"]):
                        main()

    def test_verbose_flag(self):
        """-v/--verbose sets DEBUG log level."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging") as mock_setup:
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-v"]):
                        main()

                    mock_setup.assert_called_once_with("DEBUG")

    def test_verbose_overrides_config_level(self):
        """--verbose overrides config log_level."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config(server=ServerConfig(log_level="WARNING"))
            with patch("pulse_server.__main__.setup_logging") as mock_setup:
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server", "-v"]):
                        main()

                    mock_setup.assert_called_once_with("DEBUG")

    def test_config_log_level_used_without_verbose(self):
        """Config log_level used when --verbose not specified."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config(server=ServerConfig(log_level="WARNING"))
            with patch("pulse_server.__main__.setup_logging") as mock_setup:
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(sys, "argv", ["pulse-server"]):
                        main()

                    mock_setup.assert_called_once_with("WARNING")

    def test_combined_arguments(self):
        """Multiple arguments work together."""
        with patch("pulse_server.__main__.load_config") as mock_load:
            mock_load.return_value = Config()
            with patch("pulse_server.__main__.setup_logging"):
                with patch("pulse_server.__main__.asyncio.run"):
                    with patch.object(
                        sys,
                        "argv",
                        ["pulse-server", "-H", "0.0.0.0", "-p", "8080", "-n", "Polar", "-v"],
                    ):
                        main()


class TestRunFunction:
    """Tests for run() async function."""

    @pytest.mark.asyncio
    async def test_run_with_direct_device(self):
        """run() skips scanning when device address provided."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, "AA:BB:CC:DD:EE:FF", None)

                    # Should not scan when device is provided
                    mock_scan.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_scans_when_no_device(self):
        """run() scans for devices when no device address provided."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    mock_scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_scan_with_name_filter(self):
        """run() passes name filter to scan."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "Polar H10")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, "Polar")

                    mock_scan.assert_called_once_with(
                        timeout=config.ble.scan_timeout,
                        name_filter="Polar",
                    )

    @pytest.mark.asyncio
    async def test_run_retries_scanning_when_no_devices_found(self):
        """run() retries scanning when no devices found."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            # First call returns empty, second returns a device
            mock_scan.side_effect = [[], [("AA:BB:CC:DD:EE:FF", "HR Monitor")]]
            with patch("pulse_server.__main__.asyncio.sleep") as mock_sleep:
                with patch("pulse_server.__main__.PulseServer") as MockServer:
                    with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                        mock_server = AsyncMock()
                        MockServer.return_value = mock_server

                        mock_monitor = AsyncMock()
                        mock_monitor.run = AsyncMock(return_value=None)
                        MockMonitor.return_value = mock_monitor

                        await run(config, "localhost", 8765, None, None)

                        # Should have scanned twice
                        assert mock_scan.call_count == 2
                        # Should have slept between scans
                        mock_sleep.assert_called_once_with(config.ble.scan_timeout)

    @pytest.mark.asyncio
    async def test_run_broadcasts_scanning_status(self):
        """run() broadcasts scanning status while looking for devices."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    # Should have broadcast "scanning" status
                    mock_server.broadcast_status.assert_any_call("scanning", None)

    @pytest.mark.asyncio
    async def test_run_auto_selects_single_device(self):
        """run() auto-selects when only one device found."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    # Should auto-select without prompting
                    MockMonitor.assert_called_once()
                    call_kwargs = MockMonitor.call_args[1]
                    assert call_kwargs["address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_run_auto_selects_with_name_filter(self):
        """run() auto-selects first match when name filter used."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [
                ("AA:BB:CC:DD:EE:FF", "Polar H10"),
                ("11:22:33:44:55:66", "Polar OH1"),
            ]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, "Polar")

                    # Should auto-select first match
                    call_kwargs = MockMonitor.call_args[1]
                    assert call_kwargs["address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_run_prompts_for_multiple_devices(self):
        """run() prompts user when multiple devices found without filter."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [
                ("AA:BB:CC:DD:EE:FF", "Device 1"),
                ("11:22:33:44:55:66", "Device 2"),
            ]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    with patch("builtins.input", return_value="2"):
                        with patch("builtins.print"):
                            mock_server = AsyncMock()
                            MockServer.return_value = mock_server

                            mock_monitor = AsyncMock()
                            mock_monitor.run = AsyncMock(return_value=None)
                            MockMonitor.return_value = mock_monitor

                            await run(config, "localhost", 8765, None, None)

                            # Should use selected device (2nd)
                            call_kwargs = MockMonitor.call_args[1]
                            assert call_kwargs["address"] == "11:22:33:44:55:66"

    @pytest.mark.asyncio
    async def test_run_default_selection_is_first(self):
        """run() selects first device when user presses Enter."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [
                ("AA:BB:CC:DD:EE:FF", "Device 1"),
                ("11:22:33:44:55:66", "Device 2"),
            ]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    with patch("builtins.input", return_value=""):  # Empty = default
                        with patch("builtins.print"):
                            mock_server = AsyncMock()
                            MockServer.return_value = mock_server

                            mock_monitor = AsyncMock()
                            mock_monitor.run = AsyncMock(return_value=None)
                            MockMonitor.return_value = mock_monitor

                            await run(config, "localhost", 8765, None, None)

                            # Should use first device (default)
                            call_kwargs = MockMonitor.call_args[1]
                            assert call_kwargs["address"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_run_invalid_selection_prompts_again(self):
        """run() prompts again on invalid selection."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [
                ("AA:BB:CC:DD:EE:FF", "Device 1"),
                ("11:22:33:44:55:66", "Device 2"),
            ]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    # First invalid, then valid
                    with patch("builtins.input", side_effect=["invalid", "5", "1"]):
                        with patch("builtins.print"):
                            mock_server = AsyncMock()
                            MockServer.return_value = mock_server

                            mock_monitor = AsyncMock()
                            mock_monitor.run = AsyncMock(return_value=None)
                            MockMonitor.return_value = mock_monitor

                            await run(config, "localhost", 8765, None, None)

    @pytest.mark.asyncio
    async def test_run_starts_server(self):
        """run() starts WebSocket server."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8080, None, None)

                    MockServer.assert_called_once_with(
                        host="localhost",
                        port=8080,
                        broadcast_timeout=config.server.broadcast_timeout,
                    )
                    mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_creates_monitor_with_callbacks(self):
        """run() creates monitor with server callbacks."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    call_kwargs = MockMonitor.call_args[1]
                    assert call_kwargs["on_hr"] == mock_server.broadcast_hr
                    assert call_kwargs["on_status"] == mock_server.broadcast_status

    @pytest.mark.asyncio
    async def test_run_cleanup_on_exit(self):
        """run() cleans up monitor and server on exit."""
        config = Config()

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    mock_monitor.stop.assert_called_once()
                    mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_uses_config_ble_settings(self):
        """run() uses BLE config for monitor."""
        config = Config(
            ble=BLEConfig(
                reconnect_min=0.5,
                reconnect_max=60.0,
            )
        )

        with patch("pulse_server.__main__.scan_hr_devices") as mock_scan:
            mock_scan.return_value = [("AA:BB:CC:DD:EE:FF", "HR Monitor")]
            with patch("pulse_server.__main__.PulseServer") as MockServer:
                with patch("pulse_server.__main__.PulseMonitor") as MockMonitor:
                    mock_server = AsyncMock()
                    MockServer.return_value = mock_server

                    mock_monitor = AsyncMock()
                    mock_monitor.run = AsyncMock(return_value=None)
                    MockMonitor.return_value = mock_monitor

                    await run(config, "localhost", 8765, None, None)

                    call_kwargs = MockMonitor.call_args[1]
                    assert call_kwargs["reconnect_min"] == 0.5
                    assert call_kwargs["reconnect_max"] == 60.0
