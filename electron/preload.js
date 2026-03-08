/**
 * Ashwen Electron Preload Script
 * 
 * Secure context bridge exposing only necessary APIs to the renderer process.
 * Implements principle of least privilege for Electron v28+ compatibility.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Configuration constants
const BACKEND_PORT = process.env.ASHWEN_PORT || '8000';
const BACKEND_HOST = '127.0.0.1';

/**
 * Expose protected methods that allow the renderer process to use
 * ipcRenderer without exposing the entire object.
 */
contextBridge.exposeInMainWorld('ashwen', {
  // Backend connection URLs
  backend: {
    httpUrl: `http://${BACKEND_HOST}:${BACKEND_PORT}`,
    wsUrl: `ws://${BACKEND_HOST}:${BACKEND_PORT}/ws`,
    
    /**
     * Check if backend is healthy
     * @returns {Promise<{ok: boolean, status?: string}>}
     */
    async healthCheck() {
      try {
        const response = await fetch(`http://${BACKEND_HOST}:${BACKEND_PORT}/health`, {
          signal: AbortSignal.timeout(5000)
        });
        const data = await response.json();
        return { ok: response.ok, status: data.status, data };
      } catch (err) {
        return { ok: false, error: err.message };
      }
    }
  },

  // Application information
  app: {
    version: process.env.npm_package_version || '0.1.0',
    platform: process.platform,
    arch: process.arch,
    isPackaged: !process.env.ASHWEN_DEV_SERVER_URL,
    
    /**
     * Get the app's user data path for storage
     * @returns {Promise<string>}
     */
    getUserDataPath: () => ipcRenderer.invoke('get-user-data-path'),
    
    /**
     * Get app version info
     * @returns {{version: string, name: string}}
     */
    getVersionInfo: () => ({
      version: process.env.npm_package_version || '0.1.0',
      name: 'Ashwen',
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node
    })
  },

  // File system operations (limited)
  files: {
    /**
     * Open a file dialog and return selected path
     * @param {Object} options - Dialog options
     * @returns {Promise<string|null>}
     */
    openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
    
    /**
     * Save a file dialog
     * @param {Object} options - Dialog options
     * @returns {Promise<string|null>}
     */
    saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options)
  },

  // Shell operations
  shell: {
    /**
     * Open an external URL in the default browser
     * @param {string} url - URL to open
     * @returns {Promise<void>}
     */
    openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url)
  },

  // Clipboard operations
  clipboard: {
    /**
     * Write text to clipboard
     * @param {string} text - Text to copy
     */
    writeText: (text) => ipcRenderer.invoke('clipboard:writeText', text),
    
    /**
     * Read text from clipboard
     * @returns {Promise<string>}
     */
    readText: () => ipcRenderer.invoke('clipboard:readText')
  },

  // Logging for renderer process
  log: {
    info: (message) => ipcRenderer.invoke('log:info', message),
    warn: (message) => ipcRenderer.invoke('log:warn', message),
    error: (message) => ipcRenderer.invoke('log:error', message)
  },

  // Window controls
  window: {
    /**
     * Minimize the window
     */
    minimize: () => ipcRenderer.invoke('window:minimize'),
    
    /**
     * Maximize/restore the window
     */
    toggleMaximize: () => ipcRenderer.invoke('window:toggleMaximize'),
    
    /**
     * Close the window
     */
    close: () => ipcRenderer.invoke('window:close'),
    
    /**
     * Check if window is maximized
     * @returns {Promise<boolean>}
     */
    isMaximized: () => ipcRenderer.invoke('window:isMaximized')
  },

  // Updates
  updates: {
    /**
     * Check for updates manually
     * @returns {Promise<{available: boolean, version?: string}>}
     */
    checkForUpdates: () => ipcRenderer.invoke('updates:check'),
    
    /**
     * Download and install update
     * @returns {Promise<void>}
     */
    installUpdate: () => ipcRenderer.invoke('updates:install'),
    
    /**
     * Listen for update events
     * @param {string} event - Event name
     * @param {Function} callback - Event handler
     */
    onEvent: (event, callback) => {
      const validEvents = ['update-available', 'update-downloaded', 'update-error', 'download-progress'];
      if (!validEvents.includes(event)) {
        console.warn(`Invalid update event: ${event}`);
        return () => {};
      }
      
      const subscription = (evt, data) => callback(data);
      ipcRenderer.on(`updates:${event}`, subscription);
      
      // Return unsubscribe function
      return () => ipcRenderer.removeListener(`updates:${event}`, subscription);
    }
  },

  // Analytics (privacy-first, opt-in)
  analytics: {
    /**
     * Get current analytics consent state
     * @returns {Promise<{crashReporting: boolean, productAnalytics: boolean, hasPrompted: boolean}>}
     */
    getConsent: () => ipcRenderer.invoke('analytics:getConsent'),
    
    /**
     * Set analytics consent preferences
     * @param {Object} options - Consent options
     * @param {boolean} options.crashReporting - Enable crash reporting
     * @param {boolean} options.productAnalytics - Enable product analytics
     * @returns {Promise<void>}
     */
    setConsent: (options) => ipcRenderer.invoke('analytics:setConsent', options),
    
    /**
     * Check if consent prompt should be shown
     * @returns {Promise<boolean>}
     */
    shouldPrompt: () => ipcRenderer.invoke('analytics:shouldPrompt'),
    
    /**
     * Mark consent prompt as shown
     * @returns {Promise<void>}
     */
    markPrompted: () => ipcRenderer.invoke('analytics:markPrompted'),
    
    /**
     * Track an analytics event (only if consent given)
     * @param {string} eventName - Event name
     * @param {Object} properties - Event properties
     * @returns {Promise<void>}
     */
    trackEvent: (eventName, properties) => ipcRenderer.invoke('analytics:trackEvent', eventName, properties)
  }
});

// Log preload script initialization
console.log('[Ashwen] Preload script initialized');
