"""Shared test helper functions for pulse_server tests."""

from __future__ import annotations


def make_hr_packet(
    bpm: int,
    *,
    is_16bit: bool = False,
    sensor_contact: bool | None = None,
    energy: int | None = None,
    rr_intervals: list[int] | None = None,
) -> bytes:
    """Build a BLE HR measurement packet.

    Args:
        bpm: Heart rate in BPM
        is_16bit: If True, use 16-bit BPM format
        sensor_contact: None=not supported, True=detected, False=not detected
        energy: Energy expended in joules (if supported)
        rr_intervals: RR intervals in 1/1024 second units

    Returns:
        Raw bytes for HR measurement characteristic
    """
    flags = 0

    if is_16bit:
        flags |= 0b1

    if sensor_contact is not None:
        flags |= 0b100  # Sensor contact supported
        if sensor_contact:
            flags |= 0b10  # Sensor contact detected

    if energy is not None:
        flags |= 0b1000

    if rr_intervals:
        flags |= 0b10000

    data = bytearray([flags])

    if is_16bit:
        data.extend(bpm.to_bytes(2, "little"))
    else:
        data.append(bpm)

    if energy is not None:
        data.extend(energy.to_bytes(2, "little"))

    if rr_intervals:
        for rr in rr_intervals:
            data.extend(rr.to_bytes(2, "little"))

    return bytes(data)
