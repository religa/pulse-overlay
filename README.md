# PulseOverlay

Real-time heart rate overlay for any website. Connect your BLE heart rate monitor and display your pulse while watching Netflix, YouTube, or any other site.

## Architecture

```
┌─────────────────────┐                    ┌─────────────────────┐
│   Pulse Server      │    WebSocket       │  Chrome Extension   │
│                     │    ws://localhost  │                     │
│  - Connects to BLE  │ ─────────────────► │  - Connects to WS   │
│    heart rate       │    JSON messages   │  - Injects overlay  │
│    monitor          │    {bpm: 72}       │    on any page      │
│  - Broadcasts HR    │                    │  - Displays BPM     │
└─────────────────────┘                    └─────────────────────┘
        │                                            │
        ▼                                            ▼
┌─────────────────────┐                    ┌─────────────────────┐
│  BLE Heart Rate     │                    │  Any Website        │
│  Monitor            │                    │  (Netflix, YouTube) │
└─────────────────────┘                    └─────────────────────┘
```

## Components

### [Pulse Server](server/)

Python WebSocket server that connects to BLE heart rate monitors and broadcasts data.

```bash
cd server
uv sync
uv run pulse-server -n "808S"
```

### [Chrome Extension](extension/)

Chrome extension that displays heart rate overlay on any webpage.

```bash
# Load in Chrome:
# 1. Go to chrome://extensions
# 2. Enable "Developer mode"
# 3. Click "Load unpacked" and select the extension/ folder
```

Features:
- Three display modes (minimal, standard with heart, graph)
- Configurable position and opacity
- Per-site enable/disable
- Connection status indicator

## Requirements

- Python 3.11+
- BLE-capable computer (macOS, Linux, Windows)
- Any BLE heart rate monitor (Polar, Garmin, generic chest straps, etc.)
- Chrome browser (for the extension)

## Quick Start

1. **Install the server:**
   ```bash
   cd server
   uv sync
   ```

2. **Start the server:**
   ```bash
   uv run pulse-server
   ```
   The server will scan for BLE heart rate devices and connect.

3. **Load the Chrome extension:**
   - Go to `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `extension/` folder

4. **View your heart rate:**
   - Navigate to any website
   - The overlay will appear in the corner showing your BPM
   - Click the extension icon to configure

## License

MIT
