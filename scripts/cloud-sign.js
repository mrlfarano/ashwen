/**
 * Cloud Code Signing Script
 * Supports DigiCert eSigner and Sectigo CodeSigner cloud signing services
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Configuration from environment variables
const SIGNING_SERVICE = process.env.CLOUD_SIGNING_SERVICE; // 'digicert' or 'sectigo'
const CERTIFICATE_ALIAS = process.env.CLOUD_CERT_ALIAS; // For DigiCert
const CREDENTIAL_ID = process.env.CLOUD_CREDENTIAL_ID; // For Sectigo

// DigiCert eSigner credentials
const DIGICERT_USERNAME = process.env.DIGICERT_USERNAME;
const DIGICERT_PASSWORD = process.env.DIGICERT_PASSWORD;
const DIGICERT_API_KEY = process.env.DIGICERT_API_KEY;
const DIGICERT_OTP_SECRET = process.env.DIGICERT_OTP_SECRET; // TOTP secret for 2FA

// Sectigo CodeSigner credentials
const SECTIGO_USERNAME = process.env.SECTIGO_USERNAME;
const SECTIGO_PASSWORD = process.env.SECTIGO_PASSWORD;
const SECTIGO_CLIENT_ID = process.env.SECTIGO_CLIENT_ID;
const SECTIGO_CLIENT_SECRET = process.env.SECTIGO_CLIENT_SECRET;
const SECTIGO_API_URL = process.env.SECTIGO_API_URL || 'https://cs.ssl.com';

// Signing options
const TIMESTAMP_SERVER = process.env.TIMESTAMP_SERVER || 'http://timestamp.digicert.com';
const SIGNING_ALGORITHM = process.env.SIGNING_ALGORITHM || 'sha256';

/**
 * Generate TOTP code for DigiCert 2FA
 */
function generateTOTP(secret) {
  const authenticator = require('otplib').authenticator;
  return authenticator.generate(secret);
}

/**
 * Download CodeSignTool if not present
 */
async function ensureCodeSignTool() {
  const toolPath = path.join(__dirname, '..', 'tools', 'CodeSignTool');
  const executable = process.platform === 'win32' 
    ? path.join(toolPath, 'CodeSignTool.bat')
    : path.join(toolPath, 'CodeSignTool.sh');
  
  if (fs.existsSync(executable)) {
    return executable;
  }

  console.log('📥 Downloading CodeSignTool...');
  
  // Create tools directory
  fs.mkdirSync(toolPath, { recursive: true });

  // CodeSignTool download URL (SSL.com provides this tool)
  const downloadUrl = 'https://www.ssl.com/download/codesigntool-for-windows-and-linux/';
  const zipPath = path.join(toolPath, 'CodeSignTool.zip');

  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(zipPath);
    https.get(downloadUrl, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        https.get(response.headers.location, (redirectResponse) => {
          redirectResponse.pipe(file);
          file.on('finish', () => {
            file.close();
            extractCodeSignTool(zipPath, toolPath);
            resolve(executable);
          });
        }).on('error', reject);
      } else {
        response.pipe(file);
        file.on('finish', () => {
          file.close();
          extractCodeSignTool(zipPath, toolPath);
          resolve(executable);
        });
      }
    }).on('error', reject);
  });
}

/**
 * Extract CodeSignTool archive
 */
function extractCodeSignTool(zipPath, destPath) {
  console.log('📦 Extracting CodeSignTool...');
  
  if (process.platform === 'win32') {
    execSync(`powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${destPath}' -Force"`, { stdio: 'inherit' });
  } else {
    execSync(`unzip -o "${zipPath}" -d "${destPath}"`, { stdio: 'inherit' });
  }
  
  // Make executable on Unix
  if (process.platform !== 'win32') {
    const shPath = path.join(destPath, 'CodeSignTool.sh');
    if (fs.existsSync(shPath)) {
      fs.chmodSync(shPath, '755');
    }
  }
  
  // Cleanup zip
  fs.unlinkSync(zipPath);
  console.log('✅ CodeSignTool ready');
}

/**
 * Sign file using DigiCert eSigner (via SSL.com CodeSignTool)
 */
async function signWithDigiCert(filePath) {
  console.log(`🔐 Signing with DigiCert eSigner: ${filePath}`);
  
  try {
    const codeSignTool = await ensureCodeSignTool();
    
    // Generate OTP if secret is provided
    let otp = '';
    if (DIGICERT_OTP_SECRET) {
      try {
        const otplib = require('otplib');
        otp = otplib.authenticator.generate(DIGICERT_OTP_SECRET);
        console.log('🔢 Generated TOTP code');
      } catch (error) {
        console.error('⚠️  Failed to generate TOTP. Install otplib: npm install otplib');
        throw error;
      }
    }

    // Build CodeSignTool command
    const command = [
      `"${codeSignTool}"`,
      'sign',
      `-input_file_path="${filePath}"`,
      `-username="${DIGICERT_USERNAME}"`,
      `-password="${DIGICERT_PASSWORD}"`,
      `-credential_id="${CERTIFICATE_ALIAS}"`,
      `-totp_secret="${DIGICERT_OTP_SECRET}"`,
      `-output_dir_path="${path.dirname(filePath)}"`
    ].join(' ');

    console.log('🚀 Executing cloud signing...');
    execSync(command, { 
      stdio: 'inherit',
      env: {
        ...process.env,
        DIGICERT_USERNAME,
        DIGICERT_PASSWORD,
        DIGICERT_OTP_SECRET
      }
    });

    console.log('✅ Successfully signed with DigiCert eSigner');
    return true;
  } catch (error) {
    console.error('❌ DigiCert signing failed:', error.message);
    throw error;
  }
}

/**
 * Sign file using Sectigo CodeSigner (via SSL.com API)
 */
async function signWithSectigo(filePath) {
  console.log(`🔐 Signing with Sectigo CodeSigner: ${filePath}`);
  
  try {
    const codeSignTool = await ensureCodeSignTool();
    
    // Build CodeSignTool command for Sectigo/SSL.com
    const command = [
      `"${codeSignTool}"`,
      'sign',
      `-input_file_path="${filePath}"`,
      `-username="${SECTIGO_USERNAME}"`,
      `-password="${SECTIGO_PASSWORD}"`,
      `-credential_id="${CREDENTIAL_ID}"`,
      `-output_dir_path="${path.dirname(filePath)}"`
    ].join(' ');

    console.log('🚀 Executing cloud signing...');
    execSync(command, { 
      stdio: 'inherit',
      env: {
        ...process.env,
        SECTIGO_USERNAME,
        SECTIGO_PASSWORD
      }
    });

    console.log('✅ Successfully signed with Sectigo CodeSigner');
    return true;
  } catch (error) {
    console.error('❌ Sectigo signing failed:', error.message);
    throw error;
  }
}

/**
 * Sign file using Azure Key Vault (alternative cloud signing)
 */
async function signWithAzureKeyVault(filePath) {
  console.log(`🔐 Signing with Azure Key Vault: ${filePath}`);
  
  const keyVaultUrl = process.env.AZURE_KEY_VAULT_URL;
  const certificateName = process.env.AZURE_CERTIFICATE_NAME;
  const azureClientId = process.env.AZURE_CLIENT_ID;
  const azureClientSecret = process.env.AZURE_CLIENT_SECRET;
  const azureTenantId = process.env.AZURE_TENANT_ID;

  if (!keyVaultUrl || !certificateName) {
    throw new Error('Azure Key Vault credentials not configured');
  }

  try {
    // Use AzureSignTool for signing with Azure Key Vault
    const azureSignTool = path.join(__dirname, '..', 'tools', 'AzureSignTool', 'AzureSignTool.exe');
    
    // Check if AzureSignTool is installed
    if (!fs.existsSync(azureSignTool)) {
      console.log('📥 Installing AzureSignTool...');
      execSync('dotnet tool install --tool-path ./tools/azuresigntool AzureSignTool', {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
      });
    }

    const command = [
      `"${azureSignTool}"`,
      'sign',
      `-kvu "${keyVaultUrl}"`,
      `-kvc "${certificateName}"`,
      `-kvi "${azureClientId}"`,
      `-kvs "${azureClientSecret}"`,
      `-kvt "${azureTenantId}"`,
      `-tr ${TIMESTAMP_SERVER}`,
      '-td sha256',
      `"${filePath}"`
    ].join(' ');

    console.log('🚀 Executing Azure Key Vault signing...');
    execSync(command, { stdio: 'inherit' });

    console.log('✅ Successfully signed with Azure Key Vault');
    return true;
  } catch (error) {
    console.error('❌ Azure Key Vault signing failed:', error.message);
    throw error;
  }
}

/**
 * Main signing function - routes to appropriate service
 */
async function signFile(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found: ${filePath}`);
  }

  console.log(`\n🔒 Cloud Code Signing`);
  console.log(`   Service: ${SIGNING_SERVICE || 'auto-detect'}`);
  console.log(`   File: ${filePath}\n`);

  // Auto-detect or use configured service
  if (SIGNING_SERVICE === 'digicert' || (DIGICERT_USERNAME && CERTIFICATE_ALIAS)) {
    return signWithDigiCert(filePath);
  } else if (SIGNING_SERVICE === 'sectigo' || (SECTIGO_USERNAME && CREDENTIAL_ID)) {
    return signWithSectigo(filePath);
  } else if (SIGNING_SERVICE === 'azure' || process.env.AZURE_KEY_VAULT_URL) {
    return signWithAzureKeyVault(filePath);
  } else {
    throw new Error(
      'No cloud signing service configured. Set one of:\n' +
      '  - DIGICERT_USERNAME, DIGICERT_PASSWORD, DIGICERT_OTP_SECRET, CLOUD_CERT_ALIAS\n' +
      '  - SECTIGO_USERNAME, SECTIGO_PASSWORD, CLOUD_CREDENTIAL_ID\n' +
      '  - AZURE_KEY_VAULT_URL, AZURE_CERTIFICATE_NAME, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID'
    );
  }
}

/**
 * Sign multiple files
 */
async function signFiles(filePatterns) {
  const glob = require('glob');
  
  for (const pattern of filePatterns) {
    const files = glob.sync(pattern);
    for (const file of files) {
      await signFile(file);
    }
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node cloud-sign.js <file-to-sign>');
    console.error('       node cloud-sign.js "<glob-pattern>"');
    process.exit(1);
  }

  const target = args[0];
  
  // Check if it's a glob pattern
  if (target.includes('*') || target.includes('?')) {
    signFiles([target])
      .then(() => {
        console.log('\n✅ All files signed successfully');
        process.exit(0);
      })
      .catch((error) => {
        console.error('\n❌ Signing failed:', error.message);
        process.exit(1);
      });
  } else {
    signFile(target)
      .then(() => {
        console.log('\n✅ File signed successfully');
        process.exit(0);
      })
      .catch((error) => {
        console.error('\n❌ Signing failed:', error.message);
        process.exit(1);
      });
  }
}

module.exports = {
  signFile,
  signFiles,
  signWithDigiCert,
  signWithSectigo,
  signWithAzureKeyVault
};
