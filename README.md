# PulseOverlay — Real-Time Heart Rate Overlay (BLE/Bluetooth) + Chrome Extension

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Self-hosted real-time heart rate overlay** and **heart rate monitor overlay** for streaming and any website. Connect any **BLE/Bluetooth heart rate monitor** to a Python WebSocket server and display **live BPM overlay** via a **Chrome extension**. Perfect for **streaming heart rate overlays** on Twitch, YouTube, **OBS Studio browser source overlay**, fitness tracking, gaming.

![Real-time BLE Heart Rate Overlay on Chrome Browser](https://github.com/user-attachments/assets/29a8d0f1-d7dd-413b-8137-d461f9a7f95e)

## Features: BLE Connectivity & Browser Overlay

- **Universal Chrome Extension Heart Rate Overlay** - Works on any webpage (Netflix, YouTube, Twitch, gaming sites)
- **BLE/Bluetooth Low Energy (BLE) Support** - Compatible with Polar, Garmin, Wahoo, and any standard Bluetooth heart rate sensor using BLE GATT Heart Rate Service (0x180D) / Heart Rate Measurement (0x2A37)
- **Real-time Heart Rate Display** - Low-latency WebSocket heart rate streaming with BPM + RR intervals for HRV analysis
- **Streaming Heart Rate Overlay** - Use as **OBS Studio browser source overlay** for Twitch/YouTube streams
- **Self-hosted & Privacy-Focused** - Local-first, runs on localhost, full control over your biometric data
- **Multiple Display Modes** - Minimal, standard with heart animation, or live graph view
- **Easy Installation** - Simple Chrome extension setup, no account required

## Use Cases

- **Streamers** - Add a **heart rate widget** to your Twitch or YouTube stream via **OBS Studio browser source** (window capture). Perfect for game reactions, fitness streams, and competitive gaming
- **Fitness Enthusiasts** - Monitor **real-time BPM** while watching workout videos on Netflix, YouTube, or fitness apps
- **Gamers** - Track your physiological response during horror games, competitive matches, or VR experiences
- **Content Creators** - Add engaging biometric overlays to videos and live streams without cloud dependencies
- **Researchers** - Self-hosted solution for studies requiring heart rate monitoring during web-based tasks

## Supported Devices

PulseOverlay works with any **Bluetooth Low Energy (BLE) heart rate monitor** that supports the standard BLE GATT Heart Rate Service (0x180D) and Heart Rate Measurement characteristic (0x2A37). Tested devices include:

- **Polar** - H10, H9, H7, Verity Sense, OH1
- **Garmin** - HRM-Pro, HRM-Dual, HRM-Run, Forerunner watches (broadcasting mode)
- **Wahoo** - TICKR, TICKR X, TICKR FIT
- **Coospo** - H6, H808S, HW807
- **Generic BLE Chest Straps** - Magene, CooSpo, and other BLE-compatible heart rate monitors

If your device appears in your computer's Bluetooth settings and supports heart rate monitoring, it will likely work with PulseOverlay.

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

## System Requirements

- **Python** 3.11+ (for the WebSocket server)
- **BLE-capable computer** - macOS, Linux, or Windows with Bluetooth Low Energy support
- **BLE heart rate monitor** - Polar H10, Garmin HRM-Pro, Wahoo TICKR, or any compatible device (see Supported Devices above)
- **Chrome browser** - For the heart rate overlay extension

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

## WebSocket Protocol

The server broadcasts **real-time heart rate data** via WebSocket (default: `ws://localhost:8765`). Messages are JSON-formatted:

**Heart Rate Data:**
```json
{
  "bpm": 72,
  "timestamp": 1704910800000,
  "rr_ms": [823.5, 845.2]
}
```

The `rr_ms` field contains **RR intervals** in milliseconds, useful for **HRV (Heart Rate Variability)** calculations in downstream clients.

**Status Updates:**
```json
{
  "status": "connected",
  "device": "Polar H10 ABC123"
}
```

This **WebSocket heart rate** stream can be consumed by any client (browsers, **OBS Studio**, custom applications).

## Similar Projects

- **[Pulsoid](https://pulsoid.net/)** - Cloud-based heart rate streaming service
- **[HypeRate](https://www.hyperate.io/)** - Heart rate widgets for multiple devices and platforms
- **[Stromno](https://www.stromno.com/)** - Apple Watch and Samsung Galaxy Watch streaming
- **[hr-stream](https://github.com/jakelear/hr-stream)** - Open source real-time heart rate graph for OBS
- **[hds_overlay](https://github.com/Rexios80/hds_overlay)** - Apple Watch/Android watch overlay with health data

## License

MIT
