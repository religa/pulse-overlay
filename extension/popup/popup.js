/**
 * Popup script for PulseOverlay.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const bpmValue = document.getElementById('bpm-value');
  const statusIndicator = document.getElementById('status-indicator');
  const statusText = document.getElementById('status-text');
  const siteToggle = document.getElementById('site-toggle');
  const globalToggle = document.getElementById('global-toggle');
  const reconnectBtn = document.getElementById('reconnect-btn');
  const optionsBtn = document.getElementById('options-btn');

  // Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const hostname = tab && tab.url ? new URL(tab.url).hostname : '';

  // Load settings
  const settings = await PulseState.getSettings();

  // Set initial toggle states
  globalToggle.checked = settings.enabled;
  // Site is enabled if: explicitly true OR (globally enabled AND not explicitly false)
  const siteOverride = settings.siteOverrides[hostname];
  siteToggle.checked = siteOverride === true || (settings.enabled && siteOverride !== false);

  // Bind status UI using shared helper
  PulseState.bindStatusUI({
    statusEl: statusText,
    bpmEl: bpmValue,
    statusClass: ''
  });

  // Update status indicator dot separately (it only needs state class)
  PulseState.getState().then(s => {
    statusIndicator.className = `status-indicator status-${s.connectionState}`;
  });
  PulseState.onStateChange((state) => {
    statusIndicator.className = `status-indicator status-${state}`;
  });

  // Global toggle handler
  globalToggle.addEventListener('change', async () => {
    await chrome.storage.sync.set({ enabled: globalToggle.checked });
    // Update site toggle to reflect new state
    const currentSettings = await PulseState.getSettings();
    const siteOverride = currentSettings.siteOverrides[hostname];
    siteToggle.checked = siteOverride === true || (globalToggle.checked && siteOverride !== false);
  });

  // Site toggle handler
  siteToggle.addEventListener('change', async () => {
    // Get fresh settings to avoid stale data
    const currentSettings = await PulseState.getSettings();
    const overrides = { ...currentSettings.siteOverrides } || {};

    if (siteToggle.checked) {
      // Enabling site: if global is off, explicitly enable; if global is on, remove override
      if (currentSettings.enabled) {
        delete overrides[hostname];
      } else {
        overrides[hostname] = true;
      }
    } else {
      // Disabling site: explicitly disable
      overrides[hostname] = false;
    }

    await chrome.storage.sync.set({ siteOverrides: overrides });
  });

  // Reconnect button handler
  reconnectBtn.addEventListener('click', () => {
    PulseState.requestReconnect();
  });

  // Options button handler
  optionsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
});
