# Pulse Server

[![CI](https://github.com/religa/pulse-overlay/workflows/Test/badge.svg)](https://github.com/religa/pulse-overlay/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)

A Python WebSocket server that connects to Bluetooth Low Energy (BLE) heart rate monitors and broadcasts real-time heart rate data to connected clients.

## Features

- Scans for BLE heart rate monitors (standard GATT Heart Rate Service 0x180D)
- Auto-reconnects with exponential backoff on disconnection
- Broadcasts heart rate and RR intervals via WebSocket
- Configurable via TOML file or command-line arguments
- Comprehensive test suite (153 tests, 92% coverage)

## Installation

```bash
# Install with uv
uv sync

# Or with pip
pip install -e ".[dev]"
```

## Usage

```bash
# Scan for devices and connect
uv run pulse-server

# Filter by device name (case-insensitive)
uv run pulse-server -n "808S"

# Connect to specific device address
uv run pulse-server -d "AA:BB:CC:DD:EE:FF"

# Custom host/port
uv run pulse-server -H 0.0.0.0 -p 9000

# Verbose logging
uv run pulse-server -v
```

### Command-line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-H, --host` | Server host | `127.0.0.1` |
| `-p, --port` | Server port | `8765` |
| `-d, --device` | Device address (skip scanning) | - |
| `-n, --name` | Filter devices by name | - |
| `-v, --verbose` | Enable debug logging | `false` |

## Configuration

Configuration is loaded from (in order):
1. `./config.toml`
2. `~/.config/pulse-server/config.toml`

Example `config.toml`:

```toml
[server]
host = "127.0.0.1"
port = 8765
broadcast_timeout = 0.5
log_level = "INFO"

[ble]
scan_timeout = 5.0
reconnect_min = 1.0
reconnect_max = 30.0

[device]
address = ""          # Skip scanning, connect directly
name_filter = "808S"  # Auto-connect to first match
```

## WebSocket API

Connect to `ws://localhost:8765` (or your configured host/port).

### Messages (server -> client)

**Heart rate data:**
```json
{"bpm": 72, "timestamp": 1704910800000, "rr_ms": [823.5, 815.2]}
```

**Status updates:**
```json
{"status": "scanning"}
{"status": "connecting"}
{"status": "connected", "device": "808S 0001644"}
{"status": "disconnected"}
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ --cov=pulse_server --cov-report=term-missing

# Run linter
uv run ruff check .

# Run linter with auto-fix
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check formatting (no changes)
uv run ruff format . --check

# Run type checker
uv run pyright
```

## Requirements

- Python 3.11+
- macOS, Linux, or Windows with BLE support (Windows not tested)
- A BLE heart rate monitor (any device supporting standard Heart Rate Service)

## License

MIT
