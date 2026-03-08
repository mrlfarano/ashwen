/**
 * Apple Notarization Script
 * 
 * This script handles Apple notarization for macOS builds.
 * Requires APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, and APPLE_TEAM_ID environment variables.
 * 
 * Run as afterSign hook in electron-builder.
 * 
 * Setup:
 * 1. Create an App-Specific Password at appleid.apple.com
 * 2. Store credentials in GitHub Actions secrets:
 *    - APPLE_ID: Your Apple Developer account email
 *    - APPLE_APP_SPECIFIC_PASSWORD: App-specific password
 *    - APPLE_TEAM_ID: Your Team ID (found in developer.apple.com)
 *    - APPLE_CERTIFICATE_BASE64: Base64-encoded .p12 certificate
 *    - APPLE_CERTIFICATE_PASSWORD: Certificate password
 */

const { notarize } = require('@electron/notarize');
const path = require('path');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  
  // Only notarize on macOS
  if (electronPlatformName !== 'darwin') {
    console.log('[Notarize] Skipping: not macOS');
    return;
  }

  // Check for required environment variables
  const appleId = process.env.APPLE_ID;
  const appleIdPassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  if (!appleId || !appleIdPassword || !teamId) {
    console.log('[Notarize] Skipping: missing Apple credentials');
    console.log('[Notarize] Required: APPLE_ID, APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID');
    return;
  }

  // Skip if CI indicates we should skip signing
  if (process.env.SKIP_SIGNING === 'true') {
    console.log('[Notarize] Skipping: SKIP_SIGNING is set');
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);

  console.log(`[Notarize] Starting notarization for: ${appPath}`);
  console.log(`[Notarize] Apple ID: ${appleId}`);
  console.log(`[Notarize] Team ID: ${teamId}`);

  try {
    // Use notarytool (modern API, faster than legacy notarization)
    await notarize({
      tool: 'notarytool',
      appPath,
      appleId,
      appleIdPassword,
      teamId,
    });
    
    console.log('[Notarize] ✓ Notarization complete!');
    
    // Staple the notarization ticket to the app
    console.log('[Notarize] Stapling notarization ticket...');
    const { execSync } = require('child_process');
    
    try {
      execSync(`xcrun stapler staple "${appPath}"`, { stdio: 'inherit' });
      console.log('[Notarize] ✓ Stapling complete!');
    } catch (stapleError) {
      console.warn('[Notarize] ⚠ Stapling failed (non-fatal):', stapleError.message);
    }
    
  } catch (error) {
    console.error('[Notarize] ✗ Notarization failed:', error.message);
    
    // Provide helpful error messages
    if (error.message.includes('credentials')) {
      console.error('[Notarize] Hint: Check that APPLE_ID and APPLE_APP_SPECIFIC_PASSWORD are correct');
    } else if (error.message.includes('team')) {
      console.error('[Notarize] Hint: Verify APPLE_TEAM_ID matches your developer account');
    } else if (error.message.includes('signature')) {
      console.error('[Notarize] Hint: The app may not be properly signed. Check CSC_LINK and CSC_KEY_PASSWORD');
    }
    
    // Don't fail the build for notarization issues in CI (allows unsigned testing)
    if (process.env.CI === 'true') {
      console.log('[Notarize] Continuing build despite notarization failure (CI mode)');
      console.log('[Notarize] The app will run but may show Gatekeeper warnings on macOS');
    } else {
      throw error;
    }
  }
};
