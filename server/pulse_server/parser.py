"""Heart rate measurement parser following BLE HR specification.

Parsing logic adapted from iron-heart (Rust) for full spec compliance.
"""

from dataclasses import dataclass


@dataclass
class HeartRateMeasurement:
    """Parsed heart rate measurement data."""

    bpm: int
    sensor_contact: bool | None  # None if not supported
    energy_expended: int | None  # Joules, if supported
    rr_intervals_ms: list[float]  # RR intervals in milliseconds


def parse_heart_rate(data: bytes) -> HeartRateMeasurement:
    """Parse BLE heart rate measurement characteristic data.

    Args:
        data: Raw bytes from HR measurement characteristic (0x2A37)

    Returns:
        HeartRateMeasurement with parsed values

    Raises:
        ValueError: If data is empty or malformed
    """
    if not data:
        raise ValueError("Empty HR data received")

    flags = data[0]

    # Bit 0: HR format (0 = uint8, 1 = uint16)
    is_16_bit = flags & 0b1 == 1
    # Bit 2: Sensor contact feature supported
    has_sensor_contact = flags & 0b100 == 0b100
    # Bit 3: Energy expended present
    has_energy = flags & 0b1000 == 0b1000
    # Bit 4: RR intervals present
    has_rr = flags & 0b10000 == 0b10000

    # Calculate minimum required length
    min_len = 1 + (2 if is_16_bit else 1)
    if has_energy:
        min_len += 2
    if len(data) < min_len:
        raise ValueError(f"HR data too short: {len(data)} bytes, need {min_len}")

    # Parse heart rate value
    if is_16_bit:
        bpm = int.from_bytes(data[1:3], "little")
        offset = 3
    else:
        bpm = data[1]
        offset = 2

    # Parse sensor contact
    sensor_contact = None
    if has_sensor_contact:
        sensor_contact = flags & 0b10 == 0b10

    # Parse energy expended
    energy_expended = None
    if has_energy:
        energy_expended = int.from_bytes(data[offset : offset + 2], "little")
        offset += 2

    # Parse RR intervals (in 1/1024 seconds, convert to ms)
    rr_intervals_ms = []
    if has_rr:
        while offset + 2 <= len(data):
            rr_raw = int.from_bytes(data[offset : offset + 2], "little")
            # Convert from 1/1024 seconds to milliseconds (preserves precision)
            rr_ms = rr_raw * 1000.0 / 1024.0
            rr_intervals_ms.append(rr_ms)
            offset += 2

    return HeartRateMeasurement(
        bpm=bpm,
        sensor_contact=sensor_contact,
        energy_expended=energy_expended,
        rr_intervals_ms=rr_intervals_ms,
    )
