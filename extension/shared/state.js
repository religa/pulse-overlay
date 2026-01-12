/**
 * Shared state management for PulseOverlay extension.
 * Uses storage.local as the primary state source (most reliable for MV3).
 */

const PulseState = {
  /**
   * Get current connection state from storage.
   * @returns {Promise<{connectionState: string, connectedDevice: string|null}>}
   */
  async getState() {
    const result = await chrome.storage.local.get(['connectionState', 'connectedDevice', 'currentBpm']);
    return {
      connectionState: result.connectionState || 'disconnected',
      connectedDevice: result.connectedDevice || null,
      currentBpm: result.currentBpm || null
    };
  },

  /**
   * Subscribe to connection state changes.
   * @param {function(string, string|null)} callback - Called with (state, device)
   * @returns {function} Unsubscribe function
   */
  onStateChange(callback) {
    const listener = (changes, namespace) => {
      if (namespace === 'local' && changes.connectionState) {
        callback(
          changes.connectionState.newValue,
          changes.connectedDevice?.newValue || null
        );
      }
    };
    chrome.storage.onChanged.addListener(listener);
    return () => chrome.storage.onChanged.removeListener(listener);
  },

  /**
   * Subscribe to heart rate updates.
   * Works for both content scripts (via runtime messages) and popup/options (via storage).
   * @param {function({bpm: number, timestamp: number})} callback
   * @returns {function} Unsubscribe function
   */
  onHeartRate(callback) {
    // Listen for runtime messages (for content scripts)
    const messageListener = (message) => {
      if (message.type === 'hr') {
        callback({
          bpm: message.bpm,
          timestamp: message.timestamp
        });
      }
    };
    chrome.runtime.onMessage.addListener(messageListener);

    // Listen for storage changes (for popup/options pages)
    const storageListener = (changes, namespace) => {
      if (namespace === 'local' && changes.currentBpm) {
        callback({
          bpm: changes.currentBpm.newValue,
          timestamp: Date.now()
        });
      }
    };
    chrome.storage.onChanged.addListener(storageListener);

    return () => {
      chrome.runtime.onMessage.removeListener(messageListener);
      chrome.storage.onChanged.removeListener(storageListener);
    };
  },

  /**
   * Subscribe to settings changes.
   * @param {function} callback - Called when settings change
   * @returns {function} Unsubscribe function
   */
  onSettingsChange(callback) {
    const listener = (changes, namespace) => {
      if (namespace === 'sync') {
        callback(changes);
      }
    };
    chrome.storage.onChanged.addListener(listener);
    return () => chrome.storage.onChanged.removeListener(listener);
  },

  /**
   * Get settings from storage with defaults.
   * @returns {Promise<object>}
   */
  async getSettings() {
    const defaults = typeof PULSE_DEFAULTS !== 'undefined' ? PULSE_DEFAULTS : {};
    return chrome.storage.sync.get(defaults);
  },

  /**
   * Format state label for display.
   * @param {string} state
   * @returns {string}
   */
  formatStateLabel(state) {
    if (typeof PULSE_STATE_LABELS !== 'undefined' && PULSE_STATE_LABELS[state]) {
      return PULSE_STATE_LABELS[state];
    }
    return state.charAt(0).toUpperCase() + state.slice(1);
  },

  /**
   * Request reconnection to the server.
   */
  requestReconnect() {
    chrome.runtime.sendMessage({ type: 'reconnect' });
  },

  /**
   * Bind UI elements to state updates.
   * @param {Object} options
   * @param {HTMLElement} options.statusEl - Status indicator element
   * @param {HTMLElement} options.bpmEl - BPM value element
   * @param {string} [options.statusClass='status-indicator'] - Base class for status element
   * @returns {function} Cleanup function to unsubscribe
   */
  bindStatusUI({ statusEl, bpmEl, statusClass = 'status-indicator' }) {
    const updateStatus = (state) => {
      statusEl.className = `${statusClass} status-${state}`;
      statusEl.textContent = PulseState.formatStateLabel(state);
    };

    // Set initial state and BPM
    PulseState.getState().then(s => {
      updateStatus(s.connectionState);
      if (s.currentBpm !== null) {
        bpmEl.textContent = s.currentBpm;
      }
    });

    // Subscribe to changes
    const unsubState = PulseState.onStateChange((state) => updateStatus(state));
    const unsubHr = PulseState.onHeartRate((data) => {
      bpmEl.textContent = data.bpm;
    });

    return () => {
      unsubState();
      unsubHr();
    };
  }
};

// Export for different contexts
if (typeof window !== 'undefined') {
  window.PulseState = PulseState;
}
