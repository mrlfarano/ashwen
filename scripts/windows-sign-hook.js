/**
 * Electron Builder Signing Hook for Windows
 * This script is called by electron-builder to sign Windows executables
 * It supports both traditional PFX certificates and cloud signing services
 */

const { signFile } = require('./cloud-sign');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * Sign using traditional PFX certificate
 */
function signWithPFX(filePath, certPath, password) {
  console.log(`🔐 Signing with PFX certificate: ${filePath}`);
  
  const timestampServer = process.env.TIMESTAMP_SERVER || 'http://timestamp.digicert.com';
  const signtool = findSignTool();
  
  const command = [
    `"${signtool}"`,
    'sign',
    '/fd sha256',
    '/tr', timestampServer,
    '/td sha256',
    '/f', `"${certPath}"`,
    '/p', `"${password}"`,
    `"${filePath}"`
  ].join(' ');

  execSync(command, { stdio: 'inherit' });
  console.log('✅ Successfully signed with PFX');
}

/**
 * Find signtool.exe on Windows
 */
function findSignTool() {
  const searchPaths = [
    'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.22621.0\\x64\\signtool.exe',
    'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.22000.0\\x64\\signtool.exe',
    'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.19041.0\\x64\\signtool.exe',
    'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\x64\\signtool.exe',
  ];

  for (const searchPath of searchPaths) {
    if (fs.existsSync(searchPath)) {
      return searchPath;
    }
  }

  // Try to find it dynamically
  try {
    const result = execSync(
      'where /R "C:\\Program Files (x86)\\Windows Kits\\10" signtool.exe',
      { encoding: 'utf8' }
    ).trim();
    
    const matches = result.split('\n');
    if (matches.length > 0) {
      // Prefer the highest version
      const sorted = matches.sort().reverse();
      return sorted[0].trim();
    }
  } catch (error) {
    // Ignore error
  }

  throw new Error('signtool.exe not found. Please ensure Windows SDK is installed.');
}

/**
 * Custom signing function for electron-builder
 * This is called by electron-builder during the build process
 * 
 * Configuration in electron-builder.yml:
 *   win:
 *     sign: scripts/windows-sign-hook.js
 */
module.exports = async function (configuration) {
  const filePath = configuration.path;
  
  if (!fs.existsSync(filePath)) {
    throw new Error(`File to sign not found: ${filePath}`);
  }

  console.log(`\n🔐 Windows Code Signing Hook`);
  console.log(`   File: ${filePath}`);
  console.log(`   Configuration: ${JSON.stringify(configuration, null, 2)}\n`);

  // Check if cloud signing is enabled
  const useCloudSigning = process.env.USE_CLOUD_SIGNING === 'true';
  const cloudService = process.env.CLOUD_SIGNING_SERVICE;

  if (useCloudSigning && cloudService) {
    console.log(`Using cloud signing service: ${cloudService}`);
    await signFile(filePath);
  } else if (process.env.WIN_CSC_LINK && process.env.WIN_CSC_KEY_PASSWORD) {
    console.log('Using traditional PFX certificate');
    signWithPFX(filePath, process.env.WIN_CSC_LINK, process.env.WIN_CSC_KEY_PASSWORD);
  } else {
    console.log('⚠️  No signing credentials configured, skipping signing');
    // Return without signing - this allows unsigned builds for testing
  }
};
