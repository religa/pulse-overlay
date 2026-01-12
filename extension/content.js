/**
 * Content script for PulseOverlay.
 * Initializes the overlay on web pages.
 */

(function() {
  'use strict';

  // Don't run on extension pages
  if (window.location.protocol === 'chrome-extension:') {
    return;
  }

  // Initialize overlay when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOverlay);
  } else {
    initOverlay();
  }

  function initOverlay() {
    // Wait for overlay class to be available
    if (typeof PulseOverlay === 'undefined') {
      console.error('PulseOverlay: Overlay class not loaded');
      return;
    }

    const overlay = new PulseOverlay();
    overlay.init();
  }
})();
