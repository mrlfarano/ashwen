/**
 * Ashwen Analytics Module
 * 
 * Privacy-first crash reporting and product analytics:
 * - Sentry for crash reporting with release tracking
 * - PostHog for product analytics (opt-in only)
 * - All analytics respect user consent and local-first privacy
 */

const { app } = require('electron');
const log = require('electron-log');
const fs = require('fs');
const path = require('path');

// Lazy-loaded modules (loaded only if consent given)
let Sentry = null;
let PostHog = null;

// Analytics state
let analyticsInitialized = false;
let consentState = {
  crashReporting: false,
  productAnalytics: false,
  hasPrompted: false
};

// Configuration
const SENTRY_DSN = process.env.SENTRY_DSN || null; // Set via environment or build config
const POSTHOG_KEY = process.env.POSTHOG_KEY || null; // Set via environment or build config
const POSTHOG_HOST = 'https://app.posthog.com';

// Consent file path
function getConsentFilePath() {
  return path.join(app.getPath('userData'), 'analytics-consent.json');
}

/**
 * Load consent state from disk
 */
function loadConsentState() {
  try {
    const consentPath = getConsentFilePath();
    if (fs.existsSync(consentPath)) {
      const data = JSON.parse(fs.readFileSync(consentPath, 'utf-8'));
      consentState = { ...consentState, ...data };
      log.info(`[Analytics] Loaded consent state: crash=${consentState.crashReporting}, analytics=${consentState.productAnalytics}`);
    }
  } catch (err) {
    log.warn(`[Analytics] Failed to load consent state: ${err.message}`);
  }
  return consentState;
}

/**
 * Save consent state to disk
 */
function saveConsentState() {
  try {
    const consentPath = getConsentFilePath();
    fs.writeFileSync(consentPath, JSON.stringify(consentState, null, 2));
    log.info(`[Analytics] Saved consent state`);
  } catch (err) {
    log.error(`[Analytics] Failed to save consent state: ${err.message}`);
  }
}

/**
 * Get current consent state
 */
function getConsent() {
  return { ...consentState };
}

/**
 * Update consent preferences
 * @param {Object} options - Consent options
 * @param {boolean} options.crashReporting - Enable crash reporting
 * @param {boolean} options.productAnalytics - Enable product analytics
 */
async function setConsent({ crashReporting, productAnalytics }) {
  const previousCrash = consentState.crashReporting;
  const previousAnalytics = consentState.productAnalytics;

  consentState.crashReporting = crashReporting;
  consentState.productAnalytics = productAnalytics;
  consentState.hasPrompted = true;
  
  saveConsentState();

  // Initialize or update services based on consent changes
  if (crashReporting && !previousCrash) {
    await initSentry();
  } else if (!crashReporting && previousCrash && Sentry) {
    // Sentry doesn't support disabling at runtime, but we can close it
    log.info('[Analytics] Crash reporting disabled - will take effect after restart');
  }

  if (productAnalytics && !previousAnalytics) {
    await initPostHog();
  } else if (!productAnalytics && previousAnalytics && PostHog) {
    try {
      await PostHog.shutdown();
      PostHog = null;
      log.info('[Analytics] PostHog shutdown complete');
    } catch (err) {
      log.warn(`[Analytics] PostHog shutdown error: ${err.message}`);
    }
  }

  log.info(`[Analytics] Consent updated: crash=${crashReporting}, analytics=${productAnalytics}`);
}

/**
 * Initialize Sentry for crash reporting
 */
async function initSentry() {
  if (!SENTRY_DSN) {
    log.info('[Analytics] Sentry DSN not configured, skipping crash reporting init');
    return;
  }

  if (!consentState.crashReporting) {
    log.info('[Analytics] Crash reporting consent not given, skipping Sentry init');
    return;
  }

  try {
    Sentry = require('@sentry/electron/main');
    
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: process.env.NODE_ENV || (app.isPackaged ? 'production' : 'development'),
      release: `ashwen-desktop@${app.getVersion()}`,
      
      // Only send in production
      beforeSend: (event) => {
        if (!app.isPackaged) {
          return null; // Don't send events in development
        }
        return event;
      },

      // Privacy-focused configuration
      sendDefaultPii: false, // Don't send personally identifiable info
      attachStacktrace: true,
      
      // Sample rate for performance monitoring (10%)
      tracesSampleRate: 0.1,
      
      // Integrate with electron-log
      integrations: [
        new Sentry.Integrations.ElectronLog({ log })
      ]
    });

    log.info(`[Analytics] Sentry initialized (v${app.getVersion()})`);
  } catch (err) {
    log.error(`[Analytics] Failed to initialize Sentry: ${err.message}`);
  }
}

/**
 * Initialize PostHog for product analytics
 */
async function initPostHog() {
  if (!POSTHOG_KEY) {
    log.info('[Analytics] PostHog key not configured, skipping product analytics init');
    return;
  }

  if (!consentState.productAnalytics) {
    log.info('[Analytics] Product analytics consent not given, skipping PostHog init');
    return;
  }

  try {
    const { PostHog } = require('posthog-node');
    
    PostHog = new PostHog(POSTHOG_KEY, {
      host: POSTHOG_HOST,
      flushAt: 10, // Flush after 10 events
      flushInterval: 10000, // Or every 10 seconds
      requestTimeout: 10000
    });

    // Capture app launch event
    const distinctId = getAnonymousId();
    PostHog.capture({
      distinctId,
      event: 'app_launched',
      properties: {
        version: app.getVersion(),
        platform: process.platform,
        arch: process.arch
      }
    });

    log.info(`[Analytics] PostHog initialized`);
  } catch (err) {
    log.error(`[Analytics] Failed to initialize PostHog: ${err.message}`);
  }
}

/**
 * Get or create an anonymous user ID for analytics
 * Uses a persistent random UUID stored in user data
 */
function getAnonymousId() {
  const idPath = path.join(app.getPath('userData'), 'analytics-id.json');
  
  try {
    if (fs.existsSync(idPath)) {
      const data = JSON.parse(fs.readFileSync(idPath, 'utf-8'));
      if (data.anonymousId) {
        return data.anonymousId;
      }
    }
  } catch (err) {
    log.warn(`[Analytics] Failed to read anonymous ID: ${err.message}`);
  }

  // Generate new anonymous ID
  const { randomUUID } = require('crypto');
  const anonymousId = randomUUID();
  
  try {
    fs.writeFileSync(idPath, JSON.stringify({ anonymousId, created: new Date().toISOString() }));
  } catch (err) {
    log.warn(`[Analytics] Failed to save anonymous ID: ${err.message}`);
  }

  return anonymousId;
}

/**
 * Initialize analytics system
 * Called from main process after app.whenReady()
 */
async function initialize() {
  if (analyticsInitialized) {
    return;
  }

  loadConsentState();
  
  // Initialize Sentry if consent was previously given
  if (consentState.crashReporting) {
    await initSentry();
  }

  // Initialize PostHog if consent was previously given
  if (consentState.productAnalytics) {
    await initPostHog();
  }

  analyticsInitialized = true;
  log.info('[Analytics] Analytics system initialized');
}

/**
 * Shutdown analytics gracefully
 */
async function shutdown() {
  if (PostHog) {
    try {
      await PostHog.shutdown();
      log.info('[Analytics] PostHog shutdown complete');
    } catch (err) {
      log.warn(`[Analytics] PostHog shutdown error: ${err.message}`);
    }
  }
}

/**
 * Track an analytics event (only if consent given)
 * @param {string} eventName - Name of the event
 * @param {Object} properties - Event properties
 */
function trackEvent(eventName, properties = {}) {
  if (!PostHog || !consentState.productAnalytics) {
    return;
  }

  try {
    const distinctId = getAnonymousId();
    PostHog.capture({
      distinctId,
      event: eventName,
      properties: {
        ...properties,
        version: app.getVersion(),
        platform: process.platform
      }
    });
    log.debug(`[Analytics] Event tracked: ${eventName}`);
  } catch (err) {
    log.warn(`[Analytics] Failed to track event: ${err.message}`);
  }
}

/**
 * Capture an exception in Sentry (only if consent given)
 * @param {Error} error - Error to capture
 * @param {Object} context - Additional context
 */
function captureException(error, context = {}) {
  if (!Sentry || !consentState.crashReporting) {
    return;
  }

  try {
    Sentry.captureException(error, { extra: context });
    log.debug(`[Analytics] Exception captured: ${error.message}`);
  } catch (err) {
    log.warn(`[Analytics] Failed to capture exception: ${err.message}`);
  }
}

/**
 * Check if first-run consent prompt should be shown
 */
function shouldPromptForConsent() {
  return !consentState.hasPrompted;
}

/**
 * Mark that consent prompt has been shown (user dismissed without choosing)
 */
function markConsentPrompted() {
  consentState.hasPrompted = true;
  saveConsentState();
}

/**
 * Add breadcrumb to Sentry for debugging context
 * @param {string} message - Breadcrumb message
 * @param {string} category - Breadcrumb category
 */
function addBreadcrumb(message, category = 'app') {
  if (!Sentry || !consentState.crashReporting) {
    return;
  }

  try {
    Sentry.addBreadcrumb({
      message,
      category,
      timestamp: Date.now() / 1000
    });
  } catch (err) {
    // Silently ignore breadcrumb errors
  }
}

module.exports = {
  initialize,
  shutdown,
  getConsent,
  setConsent,
  trackEvent,
  captureException,
  addBreadcrumb,
  shouldPromptForConsent,
  markConsentPrompted,
  getAnonymousId
};
