"""Tests for pulse_server.parser module."""

import pytest

from pulse_server.parser import HeartRateMeasurement, parse_heart_rate
from tests.helpers import make_hr_packet


class TestParseHeartRate:
    """Tests for parse_heart_rate function."""

    # Basic BPM parsing tests

    def test_parse_8bit_bpm(self, hr_packet_simple):
        """Parse simple 8-bit BPM value."""
        result = parse_heart_rate(hr_packet_simple)
        assert result.bpm == 72
        assert result.sensor_contact is None
        assert result.energy_expended is None
        assert result.rr_intervals_ms == []

    def test_parse_16bit_bpm(self, hr_packet_16bit):
        """Parse 16-bit BPM value."""
        result = parse_heart_rate(hr_packet_16bit)
        assert result.bpm == 180

    def test_parse_minimum_bpm(self):
        """Parse minimum valid BPM (1)."""
        packet = make_hr_packet(1)
        result = parse_heart_rate(packet)
        assert result.bpm == 1

    def test_parse_maximum_8bit_bpm(self):
        """Parse maximum 8-bit BPM (255)."""
        packet = make_hr_packet(255)
        result = parse_heart_rate(packet)
        assert result.bpm == 255

    def test_parse_maximum_16bit_bpm(self):
        """Parse maximum 16-bit BPM (65535)."""
        packet = make_hr_packet(65535, is_16bit=True)
        result = parse_heart_rate(packet)
        assert result.bpm == 65535

    def test_parse_large_16bit_bpm(self):
        """Parse large 16-bit BPM (300)."""
        packet = make_hr_packet(300, is_16bit=True)
        result = parse_heart_rate(packet)
        assert result.bpm == 300

    # Sensor contact tests

    def test_sensor_contact_supported_and_detected(self, hr_packet_with_contact):
        """Sensor contact supported and detected."""
        result = parse_heart_rate(hr_packet_with_contact)
        assert result.sensor_contact is True

    def test_sensor_contact_supported_not_detected(self):
        """Sensor contact supported but not detected."""
        packet = make_hr_packet(70, sensor_contact=False)
        result = parse_heart_rate(packet)
        assert result.sensor_contact is False

    def test_sensor_contact_not_supported(self):
        """Sensor contact not supported."""
        packet = make_hr_packet(70)
        result = parse_heart_rate(packet)
        assert result.sensor_contact is None

    # Energy expended tests

    def test_energy_expended_present(self):
        """Energy expended field present."""
        packet = make_hr_packet(80, energy=1234)
        result = parse_heart_rate(packet)
        assert result.energy_expended == 1234

    def test_energy_expended_zero(self):
        """Energy expended is zero."""
        packet = make_hr_packet(80, energy=0)
        result = parse_heart_rate(packet)
        assert result.energy_expended == 0

    def test_energy_expended_max(self):
        """Energy expended maximum value."""
        packet = make_hr_packet(80, energy=65535)
        result = parse_heart_rate(packet)
        assert result.energy_expended == 65535

    def test_energy_expended_not_present(self):
        """Energy expended not present."""
        packet = make_hr_packet(80)
        result = parse_heart_rate(packet)
        assert result.energy_expended is None

    # RR interval tests

    def test_rr_intervals_single(self):
        """Single RR interval."""
        # 1024 units = 1000ms
        packet = make_hr_packet(75, rr_intervals=[1024])
        result = parse_heart_rate(packet)
        assert len(result.rr_intervals_ms) == 1
        assert result.rr_intervals_ms[0] == pytest.approx(1000.0, rel=0.01)

    def test_rr_intervals_multiple(self, hr_packet_with_rr):
        """Multiple RR intervals."""
        result = parse_heart_rate(hr_packet_with_rr)
        assert len(result.rr_intervals_ms) == 2
        # 840 * 1000 / 1024 = 820.3125
        assert result.rr_intervals_ms[0] == pytest.approx(820.3125, rel=0.01)
        # 860 * 1000 / 1024 = 839.84375
        assert result.rr_intervals_ms[1] == pytest.approx(839.84375, rel=0.01)

    def test_rr_intervals_conversion_precision(self):
        """RR interval conversion maintains precision."""
        # 820 units = 800.78125 ms
        packet = make_hr_packet(70, rr_intervals=[820])
        result = parse_heart_rate(packet)
        expected = 820 * 1000.0 / 1024.0
        assert result.rr_intervals_ms[0] == expected

    def test_rr_intervals_empty_when_not_present(self):
        """Empty RR intervals when flag not set."""
        packet = make_hr_packet(70)
        result = parse_heart_rate(packet)
        assert result.rr_intervals_ms == []

    # Full packet tests

    def test_full_packet_all_fields(self, hr_packet_full):
        """Parse packet with all fields populated."""
        result = parse_heart_rate(hr_packet_full)
        assert result.bpm == 150
        assert result.sensor_contact is True
        assert result.energy_expended == 1500
        assert len(result.rr_intervals_ms) == 2

    def test_packet_16bit_with_rr(self):
        """16-bit BPM with RR intervals."""
        packet = make_hr_packet(200, is_16bit=True, rr_intervals=[900])
        result = parse_heart_rate(packet)
        assert result.bpm == 200
        assert len(result.rr_intervals_ms) == 1

    def test_packet_sensor_contact_with_energy(self):
        """Sensor contact and energy fields together."""
        packet = make_hr_packet(90, sensor_contact=True, energy=500)
        result = parse_heart_rate(packet)
        assert result.sensor_contact is True
        assert result.energy_expended == 500

    # Error cases

    def test_empty_data_raises_error(self):
        """Empty data raises ValueError."""
        with pytest.raises(ValueError, match="Empty HR data"):
            parse_heart_rate(b"")

    def test_too_short_8bit_data(self):
        """Data too short for 8-bit BPM."""
        with pytest.raises(ValueError, match="too short"):
            parse_heart_rate(bytes([0x00]))  # Just flags, no BPM

    def test_too_short_16bit_data(self):
        """Data too short for 16-bit BPM."""
        with pytest.raises(ValueError, match="too short"):
            parse_heart_rate(bytes([0x01, 0x50]))  # 16-bit flag, only 1 byte of BPM

    def test_too_short_with_energy_flag(self):
        """Data too short when energy flag is set."""
        # Flags: 8-bit BPM + energy, but no energy bytes
        with pytest.raises(ValueError, match="too short"):
            parse_heart_rate(bytes([0x08, 0x50]))

    # Flag combinations (2^4 = 16)

    def test_flags_0000(self):
        """Flags: none (8-bit BPM only)."""
        packet = bytes([0b0000, 72])
        result = parse_heart_rate(packet)
        assert result.bpm == 72
        assert result.sensor_contact is None
        assert result.energy_expended is None
        assert result.rr_intervals_ms == []

    def test_flags_0001(self):
        """Flags: 16-bit BPM only."""
        packet = bytes([0b0001, 0xC8, 0x00])  # 200 as little-endian
        result = parse_heart_rate(packet)
        assert result.bpm == 200

    def test_flags_0010(self):
        """Flags: sensor contact status bit (contact supported bit not set)."""
        # When bit 2 is 0 (not supported), bit 1 is ignored
        packet = bytes([0b0010, 72])
        result = parse_heart_rate(packet)
        assert result.sensor_contact is None

    def test_flags_0100(self):
        """Flags: sensor contact supported, not detected."""
        packet = bytes([0b0100, 72])
        result = parse_heart_rate(packet)
        assert result.sensor_contact is False

    def test_flags_0110(self):
        """Flags: sensor contact supported and detected."""
        packet = bytes([0b0110, 72])
        result = parse_heart_rate(packet)
        assert result.sensor_contact is True

    def test_flags_1000(self):
        """Flags: energy expended present."""
        packet = bytes([0b1000, 72, 0xE8, 0x03])  # 1000 joules
        result = parse_heart_rate(packet)
        assert result.energy_expended == 1000

    def test_flags_10000(self):
        """Flags: RR intervals present."""
        packet = bytes([0b10000, 72, 0x00, 0x04])  # 1024 units = 1000ms
        result = parse_heart_rate(packet)
        assert len(result.rr_intervals_ms) == 1

    def test_flags_all_set(self):
        """Flags: all features enabled."""
        # 16-bit BPM + contact + energy + RR
        packet = bytes([0b11111, 0x96, 0x00, 0xE8, 0x03, 0x00, 0x04])
        result = parse_heart_rate(packet)
        assert result.bpm == 150
        assert result.sensor_contact is True
        assert result.energy_expended == 1000
        assert len(result.rr_intervals_ms) == 1


class TestHeartRateMeasurement:
    """Tests for HeartRateMeasurement dataclass."""

    def test_dataclass_creation(self):
        """Create HeartRateMeasurement directly."""
        measurement = HeartRateMeasurement(
            bpm=75,
            sensor_contact=True,
            energy_expended=100,
            rr_intervals_ms=[800.0, 850.0],
        )
        assert measurement.bpm == 75
        assert measurement.sensor_contact is True
        assert measurement.energy_expended == 100
        assert measurement.rr_intervals_ms == [800.0, 850.0]

    def test_dataclass_equality(self):
        """HeartRateMeasurement equality."""
        m1 = HeartRateMeasurement(bpm=72, sensor_contact=None, energy_expended=None, rr_intervals_ms=[])
        m2 = HeartRateMeasurement(bpm=72, sensor_contact=None, energy_expended=None, rr_intervals_ms=[])
        assert m1 == m2

    def test_dataclass_inequality(self):
        """HeartRateMeasurement inequality."""
        m1 = HeartRateMeasurement(bpm=72, sensor_contact=None, energy_expended=None, rr_intervals_ms=[])
        m2 = HeartRateMeasurement(bpm=73, sensor_contact=None, energy_expended=None, rr_intervals_ms=[])
        assert m1 != m2
