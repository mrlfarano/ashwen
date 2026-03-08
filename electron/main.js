/**
 * Ashwen Electron Main Process
 * 
 * Hardened startup with caching, optimized backend spawning,
 * and production-ready configuration for Windows and macOS.
 */

const { app, BrowserWindow, dialog, session, protocol, net, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const crypto = require('crypto');

// Analytics module (crash reporting + product analytics)
const analytics = require('./analytics');

// Configure electron-log
log.transports.file.level = 'info';
log.transports.console.level = isDev() ? 'debug' : 'info';
log.transports.file.resolvePathFn = () => path.join(app.getPath('userData'), 'logs', 'main.log');

let mainWindow;
let backendProcess;
let backendReady = false;

// Configuration constants
const BACKEND_STARTUP_TIMEOUT_MS = 45000;
const BACKEND_HEALTH_CHECK_INTERVAL_MS = 500;
const BACKEND_HEALTH_CHECK_TIMEOUT_MS = 30000;
const CACHE_VERSION = 'v1'; // Increment when cache structure changes

function isDev() {
  return !app.isPackaged || !!process.env.ASHWEN_DEV_SERVER_URL;
}

const backendPort = process.env.ASHWEN_PORT || '8000';
const backendHost = '127.0.0.1';
const backendHttpUrl = `http://${backendHost}:${backendPort}`;
const backendWsUrl = `ws://${backendHost}:${backendPort}/ws`;

// ============================================================================
// Asset Caching System
// ============================================================================

/**
 * Get the cache directory path
 */
function getCacheDir() {
  const cachePath = path.join(app.getPath('userData'), 'Cache', 'assets');
  if (!fs.existsSync(cachePath)) {
    fs.mkdirSync(cachePath, { recursive: true });
  }
  return cachePath;
}

/**
 * Generate a cache key for a given asset URL or path
 */
function getCacheKey(source) {
  return crypto.createHash('sha256').update(`${CACHE_VERSION}:${source}`).digest('hex');
}

/**
 * Get cached asset if valid
 */
function getCachedAsset(cacheKey) {
  const cachePath = path.join(getCacheDir(), cacheKey);
  const metaPath = `${cachePath}.meta`;
  
  try {
    if (fs.existsSync(cachePath) && fs.existsSync(metaPath)) {
      const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
      const stats = fs.statSync(cachePath);
      
      // Check cache validity (7 days default)
      const maxAge = 7 * 24 * 60 * 60 * 1000;
      if (Date.now() - meta.timestamp < maxAge) {
        log.debug(`Cache hit: ${cacheKey}`);
        return { data: fs.readFileSync(cachePath), meta };
      }
    }
  } catch (err) {
    log.warn(`Cache read error: ${err.message}`);
  }
  
  return null;
}

/**
 * Store asset in cache
 */
function setCachedAsset(cacheKey, data, meta = {}) {
  try {
    const cachePath = path.join(getCacheDir(), cacheKey);
    const metaPath = `${cachePath}.meta`;
    
    fs.writeFileSync(cachePath, data);
    fs.writeFileSync(metaPath, JSON.stringify({
      ...meta,
      timestamp: Date.now(),
      version: CACHE_VERSION
    }));
    
    log.debug(`Cache stored: ${cacheKey}`);
  } catch (err) {
    log.warn(`Cache write error: ${err.message}`);
  }
}

/**
 * Clean old cache entries
 */
function cleanOldCache() {
  try {
    const cacheDir = getCacheDir();
    const files = fs.readdirSync(cacheDir);
    const maxAge = 30 * 24 * 60 * 60 * 1000; // 30 days
    let cleaned = 0;
    
    for (const file of files) {
      if (file.endsWith('.meta')) continue;
      
      const metaPath = path.join(cacheDir, `${file}.meta`);
      if (fs.existsSync(metaPath)) {
        const meta = JSON.parse(fs.readFileSync(metaPath, 'utf-8'));
        if (Date.now() - meta.timestamp > maxAge) {
          fs.unlinkSync(path.join(cacheDir, file));
          fs.unlinkSync(metaPath);
          cleaned++;
        }
      } else {
        // Orphan cache file without metadata
        fs.unlinkSync(path.join(cacheDir, file));
        cleaned++;
      }
    }
    
    if (cleaned > 0) {
      log.info(`Cleaned ${cleaned} old cache entries`);
    }
  } catch (err) {
    log.warn(`Cache cleanup error: ${err.message}`);
  }
}

// ============================================================================
// Backend Process Management
// ============================================================================

/**
 * Get the backend command based on environment
 */
function getBackendCommand() {
  if (isDev()) {
    return {
      command: process.platform === 'win32' ? 'python' : 'python3',
      args: [path.join(__dirname, '..', 'backend', 'run.py')],
      cwd: path.join(__dirname, '..'),
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONDONTWRITEBYTECODE: '1'
      }
    };
  }

  // Production: use bundled executable
  const executable = process.platform === 'win32' ? 'ashwen-backend.exe' : 'ashwen-backend';
  const backendPath = path.join(process.resourcesPath, 'backend', executable);
  
  return {
    command: backendPath,
    args: [],
    cwd: path.dirname(backendPath),
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1'
    }
  };
}

/**
 * Start the Python backend process with optimized settings
 */
function startBackend() {
  if (process.env.ASHWEN_SKIP_BACKEND === '1' || backendProcess) return;

  const backend = getBackendCommand();
  
  log.info(`Starting backend: ${backend.command} ${backend.args.join(' ')}`);
  
  // Optimized spawn options for faster startup
  const spawnOptions = {
    cwd: backend.cwd,
    env: {
      ...backend.env,
      ASHWEN_HOST: backendHost,
      ASHWEN_PORT: backendPort,
      ASHWEN_DATA_DIR: app.getPath('userData'),
      // SQLite optimizations
      SQLITE_THREADSAFE: '1',
      // Reduce Python startup overhead
      PYTHONNOUSERSITE: '1'
    },
    stdio: ['ignore', 'pipe', 'pipe'], // Capture stdout/stderr for logging
    detached: false,
    windowsHide: true // Hide console window on Windows
  };

  backendProcess = spawn(backend.command, backend.args, spawnOptions);

  // Stream backend stdout to log
  backendProcess.stdout?.on('data', (data) => {
    log.info(`[Backend] ${data.toString().trim()}`);
  });

  // Stream backend stderr to log
  backendProcess.stderr?.on('data', (data) => {
    log.error(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (err) => {
    log.error(`Backend process error: ${err.message}`);
    backendProcess = null;
  });

  backendProcess.on('exit', (code, signal) => {
    log.info(`Backend exited with code ${code}, signal ${signal}`);
    backendProcess = null;
    backendReady = false;
  });

  // Handle Windows-specific process group
  if (process.platform === 'win32') {
    // Ensure clean shutdown on Windows
    process.on('SIGINT', () => killBackend());
    process.on('SIGTERM', () => killBackend());
  }
}

/**
 * Kill the backend process gracefully
 */
function killBackend() {
  if (backendProcess) {
    log.info('Terminating backend process...');
    
    if (process.platform === 'win32') {
      // Windows: use taskkill for clean termination
      spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
    } else {
      // Unix: send SIGTERM first, then SIGKILL if needed
      backendProcess.kill('SIGTERM');
      setTimeout(() => {
        if (backendProcess && !backendProcess.killed) {
          backendProcess.kill('SIGKILL');
        }
      }, 5000);
    }
    
    backendProcess = null;
  }
}

/**
 * Wait for backend to be ready with health checks
 */
async function waitForBackend() {
  const startTime = Date.now();
  
  log.info('Waiting for backend to be ready...');

  while (Date.now() - startTime < BACKEND_HEALTH_CHECK_TIMEOUT_MS) {
    try {
      const response = await fetch(`${backendHttpUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      
      if (response.ok) {
        const data = await response.json();
        log.info(`Backend ready: ${JSON.stringify(data.status)}`);
        backendReady = true;
        return true;
      }
    } catch (err) {
      // Backend still starting, continue polling
    }

    await new Promise((resolve) => setTimeout(resolve, BACKEND_HEALTH_CHECK_INTERVAL_MS));
  }

  log.error('Backend failed to start within timeout');
  return false;
}

// ============================================================================
// Window Management
// ============================================================================

/**
 * Create the main application window
 */
function createWindow() {
  // Get screen dimensions for smart window sizing
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;
  
  // Calculate window size (80% of screen, min 1100x720)
  const windowWidth = Math.max(1100, Math.min(1440, Math.floor(screenWidth * 0.8)));
  const windowHeight = Math.max(720, Math.min(960, Math.floor(screenHeight * 0.8)));

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    minWidth: 1100,
    minHeight: 720,
    backgroundColor: '#0f1015',
    title: 'Ashwen',
    icon: getIconPath(),
    show: false, // Don't show until ready
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      spellcheck: true
    },
    // Platform-specific options
    ...(process.platform === 'darwin' && {
      titleBarStyle: 'hiddenInset',
      trafficLightPosition: { x: 15, y: 15 }
    }),
    ...(process.platform === 'win32' && {
      autoHideMenuBar: true
    })
  });

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    
    if (isDev()) {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  });

  // Handle external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      require('electron').shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  // Load the app
  loadApp();

  // Handle window close
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * Get platform-specific icon path
 */
function getIconPath() {
  if (isDev()) {
    return path.join(__dirname, '..', 'resources', 'icon.png');
  }
  
  if (process.platform === 'darwin') {
    return path.join(process.resourcesPath, 'icon.icns');
  } else if (process.platform === 'win32') {
    return path.join(process.resourcesPath, 'icon.ico');
  }
  
  return path.join(process.resourcesPath, 'icon.png');
}

/**
 * Load the application UI
 */
async function loadApp() {
  const startUrl = process.env.ASHWEN_DEV_SERVER_URL
    ? process.env.ASHWEN_DEV_SERVER_URL
    : `file://${path.join(__dirname, '..', 'frontend', 'build', 'index.html')}`;

  try {
    await mainWindow.loadURL(startUrl);
    log.info(`Loaded app from: ${startUrl}`);
  } catch (err) {
    log.error(`Failed to load app: ${err.message}`);
    
    // Show error page
    await mainWindow.loadURL(`data:text/html,
      <html>
        <head><title>Ashwen - Error</title></head>
        <body style="background:#0f1015;color:#fff;font-family:system-ui;padding:40px;">
          <h1>Failed to Load Application</h1>
          <p>${err.message}</p>
          <p>Please restart the application.</p>
        </body>
      </html>
    `);
  }
}

// ============================================================================
// Auto-Update System
// ============================================================================

/**
 * Setup automatic update handling
 */
function setupAutoUpdates() {
  if (isDev()) return;

  autoUpdater.logger = log;
  autoUpdater.autoDownload = false; // Don't auto-download, ask first
  autoUpdater.autoInstallOnAppQuit = true;
  
  // Check for updates on startup (delayed)
  setTimeout(() => {
    autoUpdater.checkForUpdates();
  }, 10000);

  autoUpdater.on('update-available', async (info) => {
    log.info(`Update available: ${info.version}`);
    
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      buttons: ['Download', 'Later'],
      defaultId: 0,
      cancelId: 1,
      title: 'Update Available',
      message: `Ashwen ${info.version} is available.`,
      detail: 'Would you like to download it now?'
    });

    if (result.response === 0) {
      autoUpdater.downloadUpdate();
    }
  });

  autoUpdater.on('update-not-available', () => {
    log.info('No updates available');
  });

  autoUpdater.on('download-progress', (progress) => {
    log.info(`Download progress: ${progress.percent.toFixed(1)}%`);
    mainWindow?.setProgressBar(progress.percent / 100);
  });

  autoUpdater.on('update-downloaded', async (info) => {
    mainWindow?.setProgressBar(-1);
    
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      buttons: ['Restart Now', 'Later'],
      defaultId: 0,
      cancelId: 1,
      title: 'Update Ready',
      message: 'A new Ashwen update has been downloaded.',
      detail: 'Restart the app to install the latest version.'
    });

    if (result.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on('error', (err) => {
    log.error(`Auto-update error: ${err.message}`);
  });
}

// ============================================================================
// IPC Handlers
// ============================================================================

/**
 * Setup IPC handlers for renderer communication
 */
function setupIpcHandlers() {
  // User data path
  ipcMain.handle('get-user-data-path', () => app.getPath('userData'));

  // File dialogs
  ipcMain.handle('dialog:openFile', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, options);
    return result.filePaths[0] || null;
  });

  ipcMain.handle('dialog:saveFile', async (event, options) => {
    const result = await dialog.showSaveDialog(mainWindow, options);
    return result.filePath || null;
  });

  // Shell operations
  ipcMain.handle('shell:openExternal', async (event, url) => {
    const { shell } = require('electron');
    await shell.openExternal(url);
  });

  // Clipboard operations
  ipcMain.handle('clipboard:writeText', async (event, text) => {
    const { clipboard } = require('electron');
    clipboard.writeText(text);
  });

  ipcMain.handle('clipboard:readText', async () => {
    const { clipboard } = require('electron');
    return clipboard.readText();
  });

  // Logging
  ipcMain.handle('log:info', (event, message) => log.info(`[Renderer] ${message}`));
  ipcMain.handle('log:warn', (event, message) => log.warn(`[Renderer] ${message}`));
  ipcMain.handle('log:error', (event, message) => log.error(`[Renderer] ${message}`));

  // Window controls
  ipcMain.handle('window:minimize', () => mainWindow?.minimize());
  ipcMain.handle('window:toggleMaximize', () => {
    if (mainWindow?.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow?.maximize();
    }
  });
  ipcMain.handle('window:close', () => mainWindow?.close());
  ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() || false);

  // Updates
  ipcMain.handle('updates:check', async () => {
    if (isDev()) return { available: false };
    try {
      const result = await autoUpdater.checkForUpdates();
      return { available: true, version: result.updateInfo.version };
    } catch (err) {
      return { available: false, error: err.message };
    }
  });

  ipcMain.handle('updates:install', async () => {
    if (!isDev()) {
      autoUpdater.quitAndInstall();
    }
  });

  // Analytics
  ipcMain.handle('analytics:getConsent', () => analytics.getConsent());
  ipcMain.handle('analytics:setConsent', async (event, options) => {
    await analytics.setConsent(options);
  });
  ipcMain.handle('analytics:shouldPrompt', () => analytics.shouldPromptForConsent());
  ipcMain.handle('analytics:markPrompted', () => analytics.markConsentPrompted());
  ipcMain.handle('analytics:trackEvent', (event, eventName, properties) => {
    analytics.trackEvent(eventName, properties);
  });
}

// ============================================================================
// Security Setup
// ============================================================================

/**
 * Configure security-related settings
 */
function setupSecurity() {
  // Disable navigation to external URLs
  app.on('web-contents-created', (event, contents) => {
    contents.on('will-navigate', (event, navigationUrl) => {
      const parsedUrl = new URL(navigationUrl);
      if (parsedUrl.origin !== backendHttpUrl && !navigationUrl.startsWith('file://')) {
        event.preventDefault();
        log.warn(`Blocked navigation to: ${navigationUrl}`);
      }
    });
  });

  // Verify certificate in production
  if (!isDev()) {
    app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
      // Only allow localhost certificates
      if (url.startsWith('https://localhost') || url.startsWith('https://127.0.0.1')) {
        event.preventDefault();
        callback(true);
      } else {
        callback(false);
      }
    });
  }
}

// ============================================================================
// App Lifecycle
// ============================================================================

/**
 * Application ready handler
 */
app.whenReady().then(async () => {
  log.info(`Ashwen starting... (v${app.getVersion()})`);
  log.info(`Platform: ${process.platform} ${process.arch}`);
  log.info(`Dev mode: ${isDev()}`);

  // Initialize analytics (crash reporting + product analytics, privacy-first)
  await analytics.initialize();

  // Setup IPC handlers
  setupIpcHandlers();

  // Setup security
  setupSecurity();

  // Clean old cache entries
  cleanOldCache();

  // Start backend
  startBackend();

  // Wait for backend to be ready
  const backendReady = process.env.ASHWEN_SKIP_BACKEND === '1' 
    ? true 
    : await waitForBackend();

  if (!backendReady) {
    log.error('Backend failed to start');
    
    await dialog.showMessageBox({
      type: 'error',
      title: 'Ashwen Failed to Start',
      message: 'The Ashwen backend service did not start correctly.',
      detail: 'Please restart the application. If the problem persists, try reinstalling Ashwen.',
      buttons: ['Quit']
    });
    
    app.quit();
    return;
  }

  // Create window
  createWindow();
  
  // Setup auto-updates
  setupAutoUpdates();

  // macOS: recreate window when clicking dock icon
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

/**
 * All windows closed handler
 */
app.on('window-all-closed', () => {
  // macOS: apps stay active until Cmd+Q
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

/**
 * Before quit handler
 */
app.on('before-quit', async () => {
  log.info('Application shutting down...');
  await analytics.shutdown();
  killBackend();
});

/**
 * Handle second instance (single instance lock)
 */
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  log.info('Another instance is already running, quitting...');
  app.quit();
} else {
  app.on('second-instance', () => {
    // Focus the main window if someone tries to open a second instance
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
  log.error(`Uncaught exception: ${err.message}`);
  log.error(err.stack);
  analytics.captureException(err, { source: 'uncaughtException' });
});

process.on('unhandledRejection', (reason) => {
  log.error(`Unhandled rejection: ${reason}`);
  if (reason instanceof Error) {
    analytics.captureException(reason, { source: 'unhandledRejection' });
  }
});
