/**
 * Shared constants for PulseOverlay extension.
 */

const PULSE_DEFAULTS = {
  enabled: true,
  serverUrl: 'ws://localhost:8765',
  displayMode: 'standard',
  position: 'bottom-right',
  opacity: 0.9,
  size: 'medium',
  graphDuration: 60,
  graphMinBpm: null,  // null = dynamic
  graphMaxBpm: null,  // null = dynamic
  siteOverrides: {}
};

const PULSE_STATE_LABELS = {
  scanning: 'Scanning...',
  connected: 'Connected',
  connecting: 'Connecting...',
  disconnected: 'Disconnected'
};

// Export for different contexts
if (typeof window !== 'undefined') {
  window.PULSE_DEFAULTS = PULSE_DEFAULTS;
  window.PULSE_STATE_LABELS = PULSE_STATE_LABELS;
}
