"""BLE heart rate monitor scanning and connection."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import time_ns

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.uuids import normalize_uuid_str

from .parser import parse_heart_rate

logger = logging.getLogger(__name__)

HR_SERVICE_UUID = normalize_uuid_str("180D")
HR_CHAR_UUID = normalize_uuid_str("2A37")
DEVICE_NAME_UUID = normalize_uuid_str("2A00")

PulseCallback = Callable[[int, list[float], int], Awaitable[None]]
StatusCallback = Callable[[str, str | None], Awaitable[None]]


async def scan_hr_devices(
    timeout: float = 5.0,
    name_filter: str | None = None,
) -> list[tuple[str, str]]:
    """Scan for BLE devices advertising Heart Rate service.

    Args:
        timeout: Scan duration in seconds
        name_filter: Optional case-insensitive substring to filter device names

    Returns:
        List of (address, name) tuples for discovered HR devices
    """
    devices: dict[str, str] = {}  # Use dict to deduplicate by address
    filter_lower = name_filter.lower() if name_filter else None

    def detection_callback(device: BLEDevice, adv: AdvertisementData) -> None:
        service_uuids = adv.service_uuids or []
        if HR_SERVICE_UUID in service_uuids:
            if device.address in devices:
                return  # Already seen this device
            name = device.name or "Unknown"
            if filter_lower is None or filter_lower in name.lower():
                logger.debug("Discovered: %s (%s)", name, device.address)
                devices[device.address] = name

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    logger.debug("Scan complete, found %d device(s)", len(devices))
    return list(devices.items())


class PulseMonitor:
    """Heart rate monitor with auto-reconnection."""

    def __init__(
        self,
        address: str,
        on_hr: PulseCallback,
        on_status: StatusCallback,
        reconnect_min: float = 1.0,
        reconnect_max: float = 30.0,
    ):
        self.address = address
        self.on_hr = on_hr
        self.on_status = on_status
        self._reconnect_min = reconnect_min
        self._reconnect_max = reconnect_max
        self._client: BleakClient | None = None
        self._running = False
        self._reconnect_delay = reconnect_min

    def _is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None and self._client.is_connected

    async def _cleanup_client(self) -> None:
        """Clean up client resources."""
        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.stop_notify(HR_CHAR_UUID)
                    await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    async def _notify_handler(self, _: object, data: bytearray) -> None:
        """Handle incoming HR notifications."""
        try:
            measurement = parse_heart_rate(bytes(data))
            timestamp_ms = time_ns() // 1_000_000
            logger.debug("HR: %d bpm, RR: %s", measurement.bpm, measurement.rr_intervals_ms)
            await self.on_hr(measurement.bpm, measurement.rr_intervals_ms, timestamp_ms)
        except Exception as e:
            logger.warning("Malformed HR packet: %s", e)

    async def _connect(self) -> bool:
        """Attempt to connect to the device."""
        try:
            logger.debug("Connecting to %s...", self.address)
            self._client = BleakClient(self.address)
            await self._client.connect()
            await self._client.start_notify(HR_CHAR_UUID, self._notify_handler)
            self._reconnect_delay = self._reconnect_min  # Reset backoff on success
            logger.debug("Connected and subscribed to HR notifications")
            return True
        except Exception as e:
            logger.warning("Connection failed: %s", e)
            await self._cleanup_client()
            return False

    async def _disconnect(self) -> None:
        """Disconnect from the device."""
        if self._is_connected():
            logger.debug("Disconnected from device")
        await self._cleanup_client()

    def _increase_backoff(self) -> None:
        """Increase reconnection delay with exponential backoff."""
        self._reconnect_delay = min(self._reconnect_delay * 2, self._reconnect_max)

    async def _read_device_name(self) -> str:
        """Read device name from GATT, fallback to address."""
        if self._client is None:
            return self.address
        try:
            name_bytes = await self._client.read_gatt_char(DEVICE_NAME_UUID)
            return name_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return self.address

    async def run(self) -> None:
        """Run the monitor with auto-reconnection."""
        self._running = True

        while self._running:
            await self.on_status("connecting", None)

            if not await self._connect():
                await self._handle_disconnection()
                continue

            name = await self._read_device_name()
            logger.info("Connected to %s", name)
            await self.on_status("connected", name)

            # Wait for disconnect
            while self._running and self._is_connected():
                await asyncio.sleep(0.5)

            await self._disconnect()
            await self._handle_disconnection()

    async def _handle_disconnection(self) -> None:
        """Handle disconnection with backoff delay."""
        if self._running:
            await self.on_status("disconnected", None)
            logger.info("Reconnecting in %.1fs...", self._reconnect_delay)
            await asyncio.sleep(self._reconnect_delay)
            self._increase_backoff()

    async def stop(self) -> None:
        """Stop the monitor."""
        logger.debug("Stopping monitor...")
        self._running = False
        await self._disconnect()
