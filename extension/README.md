# PulseOverlay Chrome Extension

A Chrome extension that displays real-time heart rate data from the Pulse Server as an overlay on any website.

## Features

- Real-time heart rate display on any webpage
- Three display modes: Minimal, Standard (with pulsing heart), Graph
- Configurable position (any corner)
- Per-site enable/disable controls
- Connection status indicator
- Settings sync across devices

## Installation

### Development Mode

1. Open Chrome and navigate to `chrome://extensions`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/` directory

### From Chrome Web Store

*Coming soon*

## Usage

1. **Start the Pulse Server:**
   ```bash
   cd server
   uv run pulse-server
   ```

2. **The overlay will appear** on any website when connected to the server.

3. **Click the extension icon** to:
   - See current heart rate and connection status
   - Enable/disable for the current site
   - Access full options

4. **Configure in Options** (right-click extension → Options):
   - Display mode (minimal/standard/graph)
   - Corner position
   - Size and opacity
   - Per-site overrides

## Display Modes

| Mode | Description |
|------|-------------|
| **Minimal** | BPM number only |
| **Standard** | BPM with pulsing heart animation |
| **Graph** | BPM with real-time rolling chart |

## Settings

### Server
- **WebSocket URL**: Default `ws://localhost:8765`

### Display
- **Mode**: Minimal, Standard, or Graph
- **Position**: Top-left, Top-right, Bottom-left, Bottom-right
- **Size**: Small, Medium, Large
- **Opacity**: 30% - 100%
- **Graph Duration**: 30s, 1m, 2m, 5m, 10m (graph mode only)

### Activation
- **Global toggle**: Enable/disable everywhere
- **Site overrides**: Per-site enable/disable rules

## File Structure

```
extension/
├── manifest.json       # Extension configuration
├── background.js       # Service worker (WebSocket)
├── content.js          # Content script (initializes overlay)
├── popup/              # Extension popup
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
├── options/            # Full options page
│   ├── options.html
│   ├── options.js
│   └── options.css
├── overlay/            # Overlay component
│   ├── overlay.js
│   ├── overlay.css
│   └── graph.js
└── icons/              # Extension icons
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Troubleshooting

### Overlay not appearing
1. Check that Pulse Server is running
2. Click extension icon to check connection status
3. Verify the site isn't in the disabled list
4. Check that global toggle is enabled

### Connection issues
1. Verify server URL in options (default: `ws://localhost:8765`)
2. Click "Reconnect" button
3. Check browser console for errors

### Overlay appears on wrong sites
- Use per-site overrides in Options to disable specific sites

## Development

The extension uses:
- Chrome Manifest V3
- Shadow DOM for style isolation
- Canvas API for graph rendering
- chrome.storage.sync for settings

## License

MIT
