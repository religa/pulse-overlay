"""Tests for pulse_server.log module."""

import logging

import pytest

from pulse_server.log import DATE_FORMAT, LOG_FORMAT, VALID_LEVELS, setup_logging


class TestValidLevels:
    """Tests for VALID_LEVELS constant."""

    def test_contains_standard_levels(self):
        """VALID_LEVELS contains all standard Python logging levels."""
        assert "DEBUG" in VALID_LEVELS
        assert "INFO" in VALID_LEVELS
        assert "WARNING" in VALID_LEVELS
        assert "ERROR" in VALID_LEVELS
        assert "CRITICAL" in VALID_LEVELS

    def test_exact_set(self):
        """VALID_LEVELS contains exactly the expected levels."""
        assert VALID_LEVELS == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class TestSetupLogging:
    """Tests for setup_logging function."""

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging after each test."""
        yield
        # Clean up loggers after test
        root = logging.getLogger()
        root.handlers.clear()
        app = logging.getLogger("pulse_server")
        app.handlers.clear()
        app.setLevel(logging.NOTSET)

    def test_default_level_is_info(self):
        """Default log level is INFO."""
        setup_logging()
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.INFO

    def test_debug_level(self):
        """DEBUG level sets app logger correctly."""
        setup_logging("DEBUG")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.DEBUG

    def test_info_level(self):
        """INFO level sets app logger correctly."""
        setup_logging("INFO")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.INFO

    def test_warning_level(self):
        """WARNING level sets app logger correctly."""
        setup_logging("WARNING")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.WARNING

    def test_error_level(self):
        """ERROR level sets app logger correctly."""
        setup_logging("ERROR")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.ERROR

    def test_critical_level(self):
        """CRITICAL level sets app logger correctly."""
        setup_logging("CRITICAL")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.CRITICAL

    def test_lowercase_level_accepted(self):
        """Lowercase level names are accepted."""
        setup_logging("debug")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.DEBUG

    def test_mixed_case_level_accepted(self):
        """Mixed case level names are accepted."""
        setup_logging("DeBuG")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.DEBUG

    def test_invalid_level_defaults_to_info(self, caplog):
        """Invalid level defaults to INFO and logs warning."""
        setup_logging("INVALID")
        app_logger = logging.getLogger("pulse_server")
        assert app_logger.level == logging.INFO

    def test_invalid_level_logs_warning(self, capsys):
        """Invalid level logs a warning message to stderr."""
        setup_logging("BADLEVEL")

        captured = capsys.readouterr()
        assert "Unknown log level" in captured.err
        assert "BADLEVEL" in captured.err

    def test_root_logger_at_warning(self):
        """Root logger is set to WARNING to suppress third-party noise."""
        setup_logging("DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_app_logger_can_be_more_verbose_than_root(self):
        """App logger can log DEBUG while root is WARNING."""
        setup_logging("DEBUG")
        app_logger = logging.getLogger("pulse_server")
        root_logger = logging.getLogger()

        assert app_logger.level == logging.DEBUG
        assert root_logger.level == logging.WARNING
        assert app_logger.isEnabledFor(logging.DEBUG)


class TestLogFormat:
    """Tests for log format constants."""

    def test_log_format_contains_placeholders(self):
        """LOG_FORMAT contains expected placeholders."""
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(name)s" in LOG_FORMAT
        assert "%(message)s" in LOG_FORMAT

    def test_date_format(self):
        """DATE_FORMAT is HH:MM:SS."""
        assert DATE_FORMAT == "%H:%M:%S"
