/**
 * Background service worker for PulseOverlay.
 * Maintains WebSocket connection to Pulse Server and broadcasts data to content scripts.
 */

// Import shared constants
importScripts('shared/constants.js');

// Connection state
let ws = null;
let isConnecting = false;
let connectionState = 'disconnected';
let currentBpm = null;
let reconnectDelay = 1000;
let reconnectTimer = null;
let reconnectStartTime = null;
let autoReconnectEnabled = true;
const RECONNECT_MAX_DELAY = 30000;
const RECONNECT_TIMEOUT = 60000; // Stop auto-reconnect after 60 seconds

/**
 * Get current settings from storage.
 */
async function getSettings() {
  const result = await chrome.storage.sync.get(PULSE_DEFAULTS);
  return result;
}

/**
 * Broadcast message to all tabs with content scripts.
 */
async function broadcast(message) {
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (tab.id && !tab.url?.startsWith('chrome://')) {
      try {
        await chrome.tabs.sendMessage(tab.id, message);
      } catch (e) {
        // Tab might not have content script loaded
      }
    }
  }
}

/**
 * Update connection state and notify all tabs.
 */
async function setConnectionState(state, device = null) {
  connectionState = state;

  // Store in local storage for extension pages to read
  await chrome.storage.local.set({ connectionState: state, connectedDevice: device });

  await broadcast({
    type: 'status',
    status: state,
    device: device
  });
}

/**
 * Connect to WebSocket server.
 */
async function connect() {
  // Guard must be synchronous (before any await) to prevent race conditions
  if (isConnecting || (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING))) {
    return;
  }
  isConnecting = true;

  const shouldConnect = await shouldBeConnected();

  if (!shouldConnect) {
    isConnecting = false;
    return;
  }

  const settings = await getSettings();

  await setConnectionState('connecting');

  try {
    ws = new WebSocket(settings.serverUrl);

    ws.onopen = async () => {
      console.log('PulseOverlay: Connected to server');
      isConnecting = false;
      reconnectDelay = 1000; // Reset backoff
      reconnectStartTime = null; // Reset reconnect timer
      autoReconnectEnabled = true; // Re-enable auto-reconnect for future disconnects
      // Set connected state immediately so UI updates even if server hasn't sent status yet
      await setConnectionState('connected');
    };

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.status) {
          // Status message from server
          await setConnectionState(data.status, data.device);
        } else if (data.bpm !== undefined) {
          // Heart rate data
          currentBpm = data.bpm;
          // Store in local storage for popup/options pages
          await chrome.storage.local.set({ currentBpm: data.bpm });
          await broadcast({
            type: 'hr',
            bpm: data.bpm,
            timestamp: data.timestamp
          });
        }
      } catch (e) {
        console.warn('PulseOverlay: Failed to parse server message:', e);
      }
    };

    ws.onclose = () => {
      ws = null;
      isConnecting = false;
      setConnectionState('disconnected');
      scheduleReconnect();
    };

    ws.onerror = (error) => {
      console.warn('PulseOverlay: WebSocket error:', error);
    };

  } catch (e) {
    isConnecting = false;
    await setConnectionState('disconnected');
    scheduleReconnect();
  }
}

/**
 * Schedule reconnection with exponential backoff.
 * Stops auto-reconnecting after RECONNECT_TIMEOUT.
 */
function scheduleReconnect() {
  if (!autoReconnectEnabled) {
    return;
  }

  // Start tracking reconnect time on first attempt
  if (reconnectStartTime === null) {
    reconnectStartTime = Date.now();
  }

  // Check if we've exceeded the timeout
  if (Date.now() - reconnectStartTime > RECONNECT_TIMEOUT) {
    console.log('PulseOverlay: Auto-reconnect timeout, waiting for manual reconnect');
    autoReconnectEnabled = false;
    reconnectStartTime = null;
    return;
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
  }
  reconnectTimer = setTimeout(async () => {
    reconnectTimer = null;
    const shouldConnect = await shouldBeConnected();
    if (shouldConnect && autoReconnectEnabled) {
      connect();
      reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_DELAY);
    }
  }, reconnectDelay);
}

/**
 * Disconnect from WebSocket server.
 */
function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  isConnecting = false;
  connectionState = 'disconnected';
  currentBpm = null;
}

// Handle messages from popup/options/content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'getState') {
    sendResponse({
      connectionState,
      currentBpm
    });
    return true;
  }

  if (message.type === 'settingsChanged') {
    handleSettingsChange(message.settings);
    return true;
  }

  if (message.type === 'reconnect') {
    disconnect();
    reconnectDelay = 1000;
    reconnectStartTime = null;
    autoReconnectEnabled = true; // Re-enable auto-reconnect on manual reconnect
    connect();
    return true;
  }
});

/**
 * Check if connection should be active.
 * True if globally enabled OR any site is explicitly enabled.
 */
async function shouldBeConnected() {
  const settings = await getSettings();
  if (settings.enabled) {
    return true;
  }
  // Check if any site is explicitly enabled
  const overrides = settings.siteOverrides || {};
  return Object.values(overrides).some(v => v === true);
}

/**
 * Handle settings changes.
 */
async function handleSettingsChange(newSettings) {
  const shouldConnect = await shouldBeConnected();

  if (!shouldConnect && connectionState !== 'disconnected') {
    disconnect();
    await broadcast({ type: 'settingsChanged' });
  } else if (shouldConnect && connectionState === 'disconnected') {
    // Reset reconnect state when settings trigger a new connection
    reconnectDelay = 1000;
    reconnectStartTime = null;
    autoReconnectEnabled = true;
    connect();
  } else {
    await broadcast({ type: 'settingsChanged' });
  }
}

// Listen for storage changes
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'sync') {
    const newSettings = {};
    for (const [key, { newValue }] of Object.entries(changes)) {
      newSettings[key] = newValue;
    }
    handleSettingsChange(newSettings);
  }
});

// Initialize on install/startup
chrome.runtime.onInstalled.addListener(async () => {
  // Set default settings if not present
  const current = await chrome.storage.sync.get(null);
  const defaults = {};
  for (const [key, value] of Object.entries(PULSE_DEFAULTS)) {
    if (!(key in current)) {
      defaults[key] = value;
    }
  }
  if (Object.keys(defaults).length > 0) {
    await chrome.storage.sync.set(defaults);
  }
  connect();
});

// Keep service worker alive with periodic alarms (MV3 workers can be suspended)
if (chrome.alarms) {
  chrome.alarms.create('keepAlive', { periodInMinutes: 1 });
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'keepAlive') {
      // Only attempt to reconnect if auto-reconnect is still enabled
      if (autoReconnectEnabled && (!ws || ws.readyState !== WebSocket.OPEN)) {
        connect();
      }
    }
  });
}

// Reconnect on service worker startup
connect();
