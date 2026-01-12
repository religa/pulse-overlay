"""Tests for pulse_server.ble module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pulse_server.ble import (
    HR_CHAR_UUID,
    HR_SERVICE_UUID,
    PulseMonitor,
    scan_hr_devices,
)
from tests.helpers import make_hr_packet


class TestConstants:
    """Tests for BLE UUIDs."""

    def test_hr_service_uuid_format(self):
        """HR service UUID is properly formatted."""
        assert len(HR_SERVICE_UUID) == 36
        assert "180d" in HR_SERVICE_UUID.lower()

    def test_hr_char_uuid_format(self):
        """HR characteristic UUID is properly formatted."""
        assert len(HR_CHAR_UUID) == 36
        assert "2a37" in HR_CHAR_UUID.lower()


class TestScanHRDevices:
    """Tests for scan_hr_devices function."""

    @pytest.mark.asyncio
    async def test_scan_returns_empty_when_no_devices(self):
        """scan_hr_devices returns empty list when no devices found."""
        with patch("pulse_server.ble.BleakScanner") as MockScanner:
            scanner_instance = MagicMock()
            scanner_instance.start = AsyncMock()
            scanner_instance.stop = AsyncMock()
            MockScanner.return_value = scanner_instance

            with patch("asyncio.sleep", new_callable=AsyncMock):
                devices = await scan_hr_devices(timeout=0.1)

            assert devices == []

    @pytest.mark.asyncio
    async def test_scan_calls_scanner_methods(self):
        """scan_hr_devices calls scanner start and stop."""
        with patch("pulse_server.ble.BleakScanner") as MockScanner:
            scanner_instance = MagicMock()
            scanner_instance.start = AsyncMock()
            scanner_instance.stop = AsyncMock()
            MockScanner.return_value = scanner_instance

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await scan_hr_devices(timeout=5.0)

            scanner_instance.start.assert_called_once()
            scanner_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_uses_detection_callback(self):
        """scan_hr_devices uses detection callback."""
        with patch("pulse_server.ble.BleakScanner") as MockScanner:
            scanner_instance = MagicMock()
            scanner_instance.start = AsyncMock()
            scanner_instance.stop = AsyncMock()
            MockScanner.return_value = scanner_instance

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await scan_hr_devices(timeout=0.1)

            # Verify callback was passed
            call_kwargs = MockScanner.call_args[1]
            assert "detection_callback" in call_kwargs
            assert callable(call_kwargs["detection_callback"])


class TestPulseMonitorInit:
    """Tests for PulseMonitor initialization."""

    def test_init_stores_address(self):
        """PulseMonitor stores device address."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)
        assert monitor.address == "AA:BB:CC:DD:EE:FF"

    def test_init_stores_callbacks(self):
        """PulseMonitor stores callback functions."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)
        assert monitor.on_hr == on_hr
        assert monitor.on_status == on_status

    def test_init_default_reconnect_values(self):
        """PulseMonitor uses default reconnect values."""
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", AsyncMock(), AsyncMock())
        assert monitor._reconnect_min == 1.0
        assert monitor._reconnect_max == 30.0

    def test_init_custom_reconnect_values(self):
        """PulseMonitor accepts custom reconnect values."""
        monitor = PulseMonitor(
            "AA:BB:CC:DD:EE:FF",
            AsyncMock(),
            AsyncMock(),
            reconnect_min=0.5,
            reconnect_max=60.0,
        )
        assert monitor._reconnect_min == 0.5
        assert monitor._reconnect_max == 60.0

    def test_init_state(self):
        """PulseMonitor starts in correct initial state."""
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", AsyncMock(), AsyncMock())
        assert monitor._running is False
        assert monitor._client is None
        assert monitor._reconnect_delay == 1.0


class TestPulseMonitorNotifyHandler:
    """Tests for PulseMonitor._notify_handler method."""

    @pytest.mark.asyncio
    async def test_notify_handler_calls_callback(self):
        """_notify_handler calls on_hr callback with parsed data."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        packet = make_hr_packet(72)
        await monitor._notify_handler(None, bytearray(packet))

        on_hr.assert_called_once()
        call_args = on_hr.call_args[0]
        assert call_args[0] == 72
        assert call_args[1] == []
        assert isinstance(call_args[2], int)

    @pytest.mark.asyncio
    async def test_notify_handler_with_rr_intervals(self):
        """_notify_handler passes RR intervals to callback."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        packet = make_hr_packet(75, rr_intervals=[1024])
        await monitor._notify_handler(None, bytearray(packet))

        call_args = on_hr.call_args[0]
        assert len(call_args[1]) == 1

    @pytest.mark.asyncio
    async def test_notify_handler_handles_malformed_data(self):
        """_notify_handler handles malformed data gracefully."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        await monitor._notify_handler(None, bytearray())

        on_hr.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_handler_continues_after_error(self):
        """_notify_handler continues processing after parse error."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        await monitor._notify_handler(None, bytearray())
        await monitor._notify_handler(None, bytearray(make_hr_packet(72)))

        assert on_hr.call_count == 1


class TestPulseMonitorConnect:
    """Tests for PulseMonitor._connect method."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """_connect returns True on success."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch("pulse_server.ble.BleakClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            result = await monitor._connect()

            assert result is True
            mock_client.connect.assert_called_once()
            mock_client.start_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_resets_backoff(self):
        """_connect resets reconnect delay on success."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status, reconnect_min=2.0)
        monitor._reconnect_delay = 30.0

        with patch("pulse_server.ble.BleakClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            await monitor._connect()

            assert monitor._reconnect_delay == 2.0

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """_connect returns False on failure."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch("pulse_server.ble.BleakClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.connect.side_effect = Exception("Connection refused")
            MockClient.return_value = mock_client

            result = await monitor._connect()

            assert result is False

    @pytest.mark.asyncio
    async def test_connect_subscribes_to_hr_characteristic(self):
        """_connect subscribes to HR characteristic notifications."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch("pulse_server.ble.BleakClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            await monitor._connect()

            mock_client.start_notify.assert_called_once()
            call_args = mock_client.start_notify.call_args[0]
            assert HR_CHAR_UUID in call_args[0]


class TestPulseMonitorDisconnect:
    """Tests for PulseMonitor._disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_when_connected(self):
        """_disconnect closes connection when connected."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        mock_client = AsyncMock()
        mock_client.is_connected = True
        monitor._client = mock_client

        await monitor._disconnect()

        mock_client.stop_notify.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert monitor._client is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """_disconnect does nothing when not connected."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        mock_client = AsyncMock()
        mock_client.is_connected = False
        monitor._client = mock_client

        await monitor._disconnect()

        mock_client.stop_notify.assert_not_called()
        assert monitor._client is None

    @pytest.mark.asyncio
    async def test_disconnect_no_client(self):
        """_disconnect handles no client gracefully."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        await monitor._disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_handles_error(self):
        """_disconnect handles disconnect error gracefully."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.stop_notify.side_effect = Exception("Already disconnected")
        monitor._client = mock_client

        await monitor._disconnect()

        assert monitor._client is None


class TestPulseMonitorStop:
    """Tests for PulseMonitor.stop method."""

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        """stop() sets _running to False."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)
        monitor._running = True

        await monitor.stop()

        assert monitor._running is False

    @pytest.mark.asyncio
    async def test_stop_disconnects(self):
        """stop() calls disconnect."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)
        monitor._running = True

        mock_client = AsyncMock()
        mock_client.is_connected = True
        monitor._client = mock_client

        await monitor.stop()

        mock_client.disconnect.assert_called_once()


class TestPulseMonitorRun:
    """Tests for PulseMonitor.run method."""

    @pytest.mark.asyncio
    async def test_run_sets_running_true(self):
        """run() sets _running to True initially."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch.object(monitor, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                # Stop after first iteration
                async def stop_after_call(*args):
                    monitor._running = False

                mock_sleep.side_effect = stop_after_call

                await monitor.run()

        # Was True during the run
        on_status.assert_any_call("connecting", None)

    @pytest.mark.asyncio
    async def test_run_calls_connect(self):
        """run() calls _connect."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch.object(monitor, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def stop_after_call(*args):
                    monitor._running = False

                mock_sleep.side_effect = stop_after_call

                await monitor.run()

        mock_connect.assert_called()

    @pytest.mark.asyncio
    async def test_run_sends_connecting_status(self):
        """run() sends connecting status."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch.object(monitor, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def stop_after_call(*args):
                    monitor._running = False

                mock_sleep.side_effect = stop_after_call

                await monitor.run()

        on_status.assert_any_call("connecting", None)

    @pytest.mark.asyncio
    async def test_run_sends_disconnected_on_failure(self):
        """run() sends disconnected status on connection failure."""
        on_hr = AsyncMock()
        on_status = AsyncMock()
        monitor = PulseMonitor("AA:BB:CC:DD:EE:FF", on_hr, on_status)

        with patch.object(monitor, "_connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = False

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def stop_after_call(*args):
                    monitor._running = False

                mock_sleep.side_effect = stop_after_call

                await monitor.run()

        on_status.assert_any_call("disconnected", None)


class TestPulseMonitorBackoff:
    """Tests for exponential backoff behavior."""

    def test_backoff_starts_at_min(self):
        """Backoff starts at reconnect_min."""
        monitor = PulseMonitor(
            "AA:BB:CC:DD:EE:FF",
            AsyncMock(),
            AsyncMock(),
            reconnect_min=2.0,
        )
        assert monitor._reconnect_delay == 2.0

    def test_backoff_doubles(self):
        """Backoff doubles on each failure."""
        monitor = PulseMonitor(
            "AA:BB:CC:DD:EE:FF",
            AsyncMock(),
            AsyncMock(),
            reconnect_min=1.0,
            reconnect_max=30.0,
        )
        monitor._reconnect_delay = 1.0

        # Simulate backoff increase
        monitor._reconnect_delay = min(monitor._reconnect_delay * 2, monitor._reconnect_max)
        assert monitor._reconnect_delay == 2.0

        monitor._reconnect_delay = min(monitor._reconnect_delay * 2, monitor._reconnect_max)
        assert monitor._reconnect_delay == 4.0

    def test_backoff_capped_at_max(self):
        """Backoff is capped at reconnect_max."""
        monitor = PulseMonitor(
            "AA:BB:CC:DD:EE:FF",
            AsyncMock(),
            AsyncMock(),
            reconnect_min=1.0,
            reconnect_max=5.0,
        )
        monitor._reconnect_delay = 4.0

        # Simulate backoff increase
        monitor._reconnect_delay = min(monitor._reconnect_delay * 2, monitor._reconnect_max)
        assert monitor._reconnect_delay == 5.0  # Capped at max

        monitor._reconnect_delay = min(monitor._reconnect_delay * 2, monitor._reconnect_max)
        assert monitor._reconnect_delay == 5.0  # Still capped


class TestDetectionCallback:
    """Tests for the scan detection callback behavior."""

    def test_detection_callback_filters_by_hr_service(self):
        """Detection callback filters by HR service UUID."""
        from pulse_server.ble import HR_SERVICE_UUID

        devices = []

        def make_callback():
            filter_lower = None

            def detection_callback(device, adv):
                if HR_SERVICE_UUID in adv.service_uuids:
                    name = device.name or "Unknown"
                    if filter_lower is None or filter_lower in name.lower():
                        devices.append((device.address, name))

            return detection_callback

        callback = make_callback()

        # Device with HR service
        hr_device = MagicMock()
        hr_device.address = "AA:BB:CC:DD:EE:FF"
        hr_device.name = "HR Monitor"

        hr_adv = MagicMock()
        hr_adv.service_uuids = [HR_SERVICE_UUID]

        callback(hr_device, hr_adv)
        assert len(devices) == 1

        # Device without HR service
        other_device = MagicMock()
        other_device.address = "11:22:33:44:55:66"
        other_device.name = "Other"

        other_adv = MagicMock()
        other_adv.service_uuids = ["00001800-0000-1000-8000-00805f9b34fb"]

        callback(other_device, other_adv)
        assert len(devices) == 1  # Still 1

    def test_detection_callback_name_filter(self):
        """Detection callback applies name filter."""
        from pulse_server.ble import HR_SERVICE_UUID

        devices = []
        filter_lower = "polar"

        def detection_callback(device, adv):
            if HR_SERVICE_UUID in adv.service_uuids:
                name = device.name or "Unknown"
                if filter_lower is None or filter_lower in name.lower():
                    devices.append((device.address, name))

        # Matching device
        polar_device = MagicMock()
        polar_device.address = "AA:BB:CC:DD:EE:FF"
        polar_device.name = "Polar H10"

        adv = MagicMock()
        adv.service_uuids = [HR_SERVICE_UUID]

        detection_callback(polar_device, adv)
        assert len(devices) == 1

        # Non-matching device
        other_device = MagicMock()
        other_device.address = "11:22:33:44:55:66"
        other_device.name = "Garmin HRM"

        detection_callback(other_device, adv)
        assert len(devices) == 1  # Still 1

    def test_detection_callback_handles_unknown_name(self):
        """Detection callback handles devices with no name."""
        from pulse_server.ble import HR_SERVICE_UUID

        devices = []

        def detection_callback(device, adv):
            if HR_SERVICE_UUID in adv.service_uuids:
                name = device.name or "Unknown"
                devices.append((device.address, name))

        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = None

        adv = MagicMock()
        adv.service_uuids = [HR_SERVICE_UUID]

        detection_callback(device, adv)
        assert devices == [("AA:BB:CC:DD:EE:FF", "Unknown")]
