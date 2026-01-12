/**
 * PulseOverlay overlay component.
 * Creates and manages the heart rate overlay on web pages.
 */

class PulseOverlay {
  constructor() {
    this.container = null;
    this.shadowRoot = null;
    this.bpmElement = null;
    this.statusElement = null;
    this.heartElement = null;
    this.graphCanvas = null;
    this.graph = null;
    this.settings = null;
    this.currentBpm = null;
    this.connectionState = 'disconnected';
    // Store unsubscribe functions for cleanup
    this._unsubscribeState = null;
    this._unsubscribeHR = null;
    this._unsubscribeSettings = null;
  }

  /**
   * Initialize the overlay.
   */
  async init() {
    this.settings = await PulseState.getSettings();

    // Always listen for settings changes so we can show overlay when enabled
    this._unsubscribeSettings = PulseState.onSettingsChange(() => {
      this.handleSettingsChange();
    });

    if (!this.settings || !this.shouldShow()) {
      return;
    }

    this.createOverlay();
    this.setupListeners();

    // Get initial state
    const state = await PulseState.getState();
    this.connectionState = state.connectionState;
    if (state.currentBpm !== null) {
      this.currentBpm = state.currentBpm;
      // Seed graph with current BPM if in graph mode
      if (this.graph) {
        this.graph.addPoint(state.currentBpm, Date.now());
      }
    }
    this.updateDisplay();
  }

  /**
   * Check if overlay should be shown on this site.
   * Shows if: site explicitly enabled OR (globally enabled AND site not explicitly disabled)
   */
  shouldShow() {
    const hostname = window.location.hostname;
    const override = this.settings.siteOverrides[hostname];

    // Site explicitly enabled - always show
    if (override === true) {
      return true;
    }

    // Site explicitly disabled - never show
    if (override === false) {
      return false;
    }

    // No override - follow global setting
    return this.settings.enabled;
  }

  /**
   * Create the overlay DOM structure.
   */
  createOverlay() {
    // Create container with Shadow DOM for style isolation
    this.container = document.createElement('div');
    this.container.id = 'pulse-overlay-container';
    this.shadowRoot = this.container.attachShadow({ mode: 'open' });

    // Inject styles
    const styles = document.createElement('style');
    styles.textContent = this.getStyles();
    this.shadowRoot.appendChild(styles);

    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = `pulse-overlay ${this.settings.position} size-${this.settings.size}`;
    overlay.style.opacity = this.settings.opacity;

    // Status indicator
    this.statusElement = document.createElement('div');
    this.statusElement.className = 'status-indicator status-disconnected';
    overlay.appendChild(this.statusElement);

    // Heart icon (for standard mode)
    this.heartElement = document.createElement('div');
    this.heartElement.className = 'heart-icon';
    this.heartElement.innerHTML = this.getHeartSvg();
    if (this.settings.displayMode === 'minimal') {
      this.heartElement.style.display = 'none';
    }
    overlay.appendChild(this.heartElement);

    // BPM display
    this.bpmElement = document.createElement('div');
    this.bpmElement.className = 'bpm-display';
    this.bpmElement.innerHTML = '<span class="bpm-value">--</span><span class="bpm-label">BPM</span>';
    overlay.appendChild(this.bpmElement);

    // Graph canvas (for graph mode)
    if (this.settings.displayMode === 'graph') {
      const graphContainer = document.createElement('div');
      graphContainer.className = 'graph-container';
      this.graphCanvas = document.createElement('canvas');
      this.graphCanvas.width = 120;
      this.graphCanvas.height = 40;
      graphContainer.appendChild(this.graphCanvas);
      overlay.appendChild(graphContainer);

      // Initialize graph
      this.graph = new PulseGraph(this.graphCanvas, this.settings.graphDuration);
    }

    this.shadowRoot.appendChild(overlay);
    document.body.appendChild(this.container);
  }

  /**
   * Get overlay CSS styles.
   */
  getStyles() {
    return `
      .pulse-overlay {
        position: fixed;
        z-index: 2147483647;
        background: rgba(0, 0, 0, 0.75);
        border-radius: 12px;
        padding: 10px 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: white;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        user-select: none;
        transition: opacity 0.3s ease;
      }

      .pulse-overlay.top-left { top: 20px; left: 20px; }
      .pulse-overlay.top-right { top: 20px; right: 20px; }
      .pulse-overlay.bottom-left { bottom: 20px; left: 20px; }
      .pulse-overlay.bottom-right { bottom: 20px; right: 20px; }

      .pulse-overlay.size-small { transform: scale(0.8); }
      .pulse-overlay.size-medium { transform: scale(1); }
      .pulse-overlay.size-large { transform: scale(1.2); }

      .status-indicator {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }

      .status-connected { background: #4CAF50; box-shadow: 0 0 6px #4CAF50; }
      .status-connecting { background: #FFC107; animation: pulse-status 1s ease-in-out infinite; }
      .status-scanning { background: #2196F3; animation: pulse-status 1s ease-in-out infinite; }
      .status-disconnected { background: #F44336; }

      @keyframes pulse-status {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }

      .heart-icon {
        width: 24px;
        height: 24px;
        flex-shrink: 0;
      }

      .heart-icon svg {
        width: 100%;
        height: 100%;
        fill: #F44336;
      }

      .heart-icon.beating svg {
        animation: heartbeat 0.8s ease-in-out infinite;
      }

      @keyframes heartbeat {
        0%, 100% { transform: scale(1); }
        15% { transform: scale(1.15); }
        30% { transform: scale(1); }
        45% { transform: scale(1.1); }
      }

      .bpm-display {
        display: flex;
        align-items: baseline;
        gap: 4px;
      }

      .bpm-value {
        font-size: 28px;
        font-weight: 600;
        line-height: 1;
        min-width: 45px;
      }

      .bpm-label {
        font-size: 12px;
        opacity: 0.7;
        text-transform: uppercase;
      }

      .pulse-overlay.disconnected {
        opacity: 0.6;
      }

      .pulse-overlay.disconnected .bpm-value {
        color: #999;
      }

      .graph-container {
        margin-left: 4px;
      }

      .graph-container canvas {
        display: block;
      }
    `;
  }

  /**
   * Get heart SVG icon.
   */
  getHeartSvg() {
    return `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
    </svg>`;
  }

  /**
   * Setup event listeners using PulseState.
   * Note: Settings listener is set up in init() to always be active.
   */
  setupListeners() {
    // Subscribe to state changes
    this._unsubscribeState = PulseState.onStateChange((state) => {
      this.connectionState = state;
      this.updateDisplay();
    });

    // Subscribe to heart rate updates
    this._unsubscribeHR = PulseState.onHeartRate((data) => {
      this.currentBpm = data.bpm;
      this.updateDisplay();

      if (this.graph) {
        this.graph.addPoint(data.bpm, data.timestamp);
      }
    });
  }

  /**
   * Handle settings change.
   */
  async handleSettingsChange() {
    const oldSettings = this.settings;
    this.settings = await PulseState.getSettings();

    if (!this.shouldShow()) {
      // Remove overlay but keep settings listener active
      this.removeOverlay();
      return;
    }

    // Recreate overlay if display mode, position, size, or opacity changed
    const needsRecreate = this.container && oldSettings && (
      oldSettings.displayMode !== this.settings.displayMode ||
      oldSettings.position !== this.settings.position ||
      oldSettings.size !== this.settings.size ||
      oldSettings.opacity !== this.settings.opacity ||
      oldSettings.graphDuration !== this.settings.graphDuration
    );

    if (needsRecreate) {
      this.removeOverlay();
    }

    if (!this.container) {
      this.createOverlay();
      this.setupListeners();

      // Get initial state
      const state = await PulseState.getState();
      this.connectionState = state.connectionState;
      if (state.currentBpm !== null) {
        this.currentBpm = state.currentBpm;
        // Seed graph with current BPM if in graph mode
        if (this.graph) {
          this.graph.addPoint(state.currentBpm, Date.now());
        }
      }
    }

    this.updateDisplay();
  }

  /**
   * Remove overlay DOM and data listeners but keep settings listener.
   */
  removeOverlay() {
    // Unsubscribe from data listeners
    if (this._unsubscribeState) {
      this._unsubscribeState();
      this._unsubscribeState = null;
    }
    if (this._unsubscribeHR) {
      this._unsubscribeHR();
      this._unsubscribeHR = null;
    }

    // Clean up graph
    if (this.graph && typeof this.graph.clear === 'function') {
      this.graph.clear();
    }

    // Remove DOM
    if (this.container) {
      this.container.remove();
    }
    this.container = null;
    this.shadowRoot = null;
    this.bpmElement = null;
    this.statusElement = null;
    this.heartElement = null;
    this.graphCanvas = null;
    this.graph = null;
  }

  /**
   * Update the overlay display.
   */
  updateDisplay() {
    if (!this.container) return;

    const overlay = this.shadowRoot.querySelector('.pulse-overlay');

    // Update status indicator
    this.statusElement.className = `status-indicator status-${this.connectionState}`;

    // Update BPM
    const bpmValue = this.bpmElement.querySelector('.bpm-value');
    if (this.currentBpm !== null && this.connectionState === 'connected') {
      bpmValue.textContent = this.currentBpm;
      this.heartElement.classList.add('beating');
      overlay.classList.remove('disconnected');
    } else {
      bpmValue.textContent = '--';
      this.heartElement.classList.remove('beating');
      overlay.classList.add('disconnected');
    }
  }

  /**
   * Destroy the overlay completely (including settings listener).
   */
  destroy() {
    // Remove overlay and data listeners
    this.removeOverlay();

    // Also remove settings listener (full cleanup)
    if (this._unsubscribeSettings) {
      this._unsubscribeSettings();
      this._unsubscribeSettings = null;
    }
  }
}

// Export for content script
window.PulseOverlay = PulseOverlay;
