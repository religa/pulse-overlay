"""Shared test fixtures for pulse_server tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from tests.helpers import make_hr_packet


@pytest.fixture
def make_hr_packet_fixture():
    """Fixture providing make_hr_packet helper for tests."""
    return make_hr_packet


@pytest.fixture
def hr_packet_simple() -> bytes:
    """Simple 8-bit BPM packet (72 bpm)."""
    return make_hr_packet(72)


@pytest.fixture
def hr_packet_16bit() -> bytes:
    """16-bit BPM packet (180 bpm)."""
    return make_hr_packet(180, is_16bit=True)


@pytest.fixture
def hr_packet_with_contact() -> bytes:
    """Packet with sensor contact detected."""
    return make_hr_packet(85, sensor_contact=True)


@pytest.fixture
def hr_packet_with_rr() -> bytes:
    """Packet with RR intervals (820ms = 840 in 1/1024s units)."""
    return make_hr_packet(75, rr_intervals=[840, 860])


@pytest.fixture
def hr_packet_full() -> bytes:
    """Packet with all fields populated."""
    return make_hr_packet(
        150,
        is_16bit=True,
        sensor_contact=True,
        energy=1500,
        rr_intervals=[800, 850],
    )


# Mock fixtures for BLE
@pytest.fixture
def mock_bleak_client():
    """Create a mock BleakClient."""
    client = AsyncMock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=b"TestDevice")

    # Mock services
    mock_services = MagicMock()
    mock_services.characteristics = {}
    type(client).services = PropertyMock(return_value=mock_services)

    return client


@pytest.fixture
def mock_ble_device():
    """Create a mock BLEDevice."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "HR Monitor"
    return device


@pytest.fixture
def mock_advertisement_data():
    """Create mock AdvertisementData with HR service UUID."""
    from bleak.uuids import normalize_uuid_str

    adv = MagicMock()
    adv.service_uuids = [normalize_uuid_str("180D")]
    return adv


# Mock fixtures for WebSocket
@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


# Config fixtures
@pytest.fixture
def sample_config_dict() -> dict:
    """Sample config dict as would be parsed from TOML."""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 9000,
            "broadcast_timeout": 1.0,
            "log_level": "DEBUG",
        },
        "ble": {
            "scan_timeout": 10.0,
            "reconnect_min": 2.0,
            "reconnect_max": 60.0,
        },
        "device": {
            "address": "11:22:33:44:55:66",
            "name_filter": "Polar",
        },
    }


@pytest.fixture
def partial_config_dict() -> dict:
    """Partial config dict with some values missing."""
    return {
        "server": {"port": 8080},
        "ble": {"scan_timeout": 3.0},
    }
