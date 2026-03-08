# Code Signing Setup Guide

This guide explains how to configure code signing for Ashwen Desktop on macOS and Windows.

## Overview

Code signing is required for:
- **macOS**: Gatekeeper approval and notarization (required for distribution outside the App Store)
- **Windows**: Authenticode verification (removes "Unknown Publisher" warnings in SmartScreen)

## Required GitHub Actions Secrets

### macOS (Apple Developer)

| Secret | Description | How to Obtain |
|--------|-------------|---------------|
| `APPLE_CERTIFICATE_BASE64` | Base64-encoded .p12 certificate | Export from Keychain, base64 encode |
| `APPLE_CERTIFICATE_PASSWORD` | Password used when exporting .p12 | Set during export |
| `APPLE_ID` | Apple Developer account email | Your Apple ID |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password | Generate at appleid.apple.com |
| `APPLE_TEAM_ID` | Team ID from Developer Portal | Found in developer.apple.com/account |

### Windows (EV Code Signing)

| Secret | Description | How to Obtain |
|--------|-------------|---------------|
| `WIN_EV_CERTIFICATE_BASE64` | Base64-encoded .pfx certificate | From your CA, base64 encode |
| `WIN_EV_CERTIFICATE_PASSWORD` | Password for the .pfx file | Set when receiving certificate |

---

## macOS Setup

### 1. Obtain Developer ID Application Certificate

1. Sign in to [Apple Developer](https://developer.apple.com/account)
2. Go to **Certificates, Identifiers & Profiles**
3. Click **Certificates** → **Create a Certificate**
4. Select **Developer ID Application** (for distribution outside App Store)
5. Follow the prompts to create and download the certificate

### 2. Export Certificate as .p12

1. Open **Keychain Access** on your Mac
2. Locate your "Developer ID Application" certificate
3. Right-click → **Export**
4. Save as `.p12` format with a strong password
5. Base64 encode the file:
   ```bash
   base64 -i certificate.p12 -o certificate_base64.txt
   ```

### 3. Create App-Specific Password

1. Go to [Apple ID Account Page](https://appleid.apple.com/)
2. Sign in → **Security** → **App-Specific Passwords**
3. Click **Generate Password**
4. Save the password (you'll only see it once)

### 4. Find Your Team ID

1. Sign in to [Apple Developer](https://developer.apple.com/account)
2. Click **Membership** in the sidebar
3. Copy your **Team ID** (10-character string)

### 5. Add Secrets to GitHub

```bash
# Using GitHub CLI
gh secret set APPLE_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set APPLE_CERTIFICATE_PASSWORD
gh secret set APPLE_ID
gh secret set APPLE_APP_SPECIFIC_PASSWORD
gh secret set APPLE_TEAM_ID
```

---

## Windows Setup

### Option 1: Traditional PFX Certificate

#### 1. Obtain EV Code Signing Certificate

For EV (Extended Validation) code signing, you need a certificate from a trusted CA:

- [DigiCert](https://www.digicert.com/signing/code-signing-certificates)
- [Sectigo](https://sectigo.com/ssl-certificates-tls/code-signing)
- [GlobalSign](https://www.globalsign.com/en/code-signing-certificate)
- [SSL.com](https://www.ssl.com/certificates/ev-code-signing/)

**Important**: EV certificates require:
- Organization verification
- Hardware token or cloud HSM (for some CAs)
- Typically costs $200-500/year

#### 2. Prepare Certificate for GitHub Actions

If you have a .pfx file:

```bash
# Base64 encode the .pfx file (on Windows PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx")) | Out-File certificate_base64.txt

# Or on Linux/macOS
base64 -i certificate.pfx -o certificate_base64.txt
```

#### 3. Add Secrets to GitHub

```bash
# Using GitHub CLI
gh secret set WIN_EV_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set WIN_EV_CERTIFICATE_PASSWORD
```

### Option 2: Cloud Signing (Recommended for CI/CD)

Cloud signing eliminates the need to manage certificate files and provides better security for CI/CD pipelines. We support three cloud signing services:

#### DigiCert eSigner

1. **Purchase DigiCert EV Code Signing Certificate**
   - Visit [DigiCert Code Signing](https://www.digicert.com/signing/code-signing-certificates)
   - Choose "eSigner" cloud signing option
   - Complete verification process

2. **Get Your Credentials**
   - Log in to DigiCert account
   - Note your certificate alias (shown in eSigner dashboard)
   - Generate an API key
   - Set up TOTP for 2FA (save the secret)

3. **Add GitHub Secrets**

```bash
gh secret set CLOUD_SIGNING_SERVICE --body "digicert"
gh secret set DIGICERT_USERNAME --body "your-email@example.com"
gh secret set DIGICERT_PASSWORD --body "your-digicert-password"
gh secret set DIGICERT_API_KEY --body "your-api-key"
gh secret set DIGICERT_OTP_SECRET --body "your-totp-secret-base32"
gh secret set CLOUD_CERT_ALIAS --body "your-certificate-alias"
```

#### Sectigo/SSL.com CodeSigner

1. **Purchase EV Code Signing Certificate from SSL.com**
   - Visit [SSL.com EV Code Signing](https://www.ssl.com/certificates/ev-code-signing/)
   - Choose cloud signing option
   - Complete verification

2. **Get Your Credentials**
   - Log in to SSL.com
   - Get your Credential ID from the dashboard
   - Create OAuth credentials (Client ID and Secret)

3. **Add GitHub Secrets**

```bash
gh secret set CLOUD_SIGNING_SERVICE --body "sectigo"
gh secret set SECTIGO_USERNAME --body "your-email@example.com"
gh secret set SECTIGO_PASSWORD --body "your-ssl-com-password"
gh secret set SECTIGO_CLIENT_ID --body "your-oauth-client-id"
gh secret set SECTIGO_CLIENT_SECRET --body "your-oauth-client-secret"
gh secret set CLOUD_CREDENTIAL_ID --body "your-credential-id"
```

#### Azure Key Vault

1. **Upload Code Signing Certificate to Azure Key Vault**
   - Create or use existing Azure Key Vault
   - Import your code signing certificate
   - Note the certificate name and Key Vault URL

2. **Create Azure AD App Registration**
   - Register an app in Azure AD
   - Grant it access to Key Vault (Key Vault Crypto User role)
   - Create a client secret

3. **Add GitHub Secrets**

```bash
gh secret set CLOUD_SIGNING_SERVICE --body "azure"
gh secret set AZURE_KEY_VAULT_URL --body "https://your-vault.vault.azure.net/"
gh secret set AZURE_CERTIFICATE_NAME --body "your-certificate-name"
gh secret set AZURE_CLIENT_ID --body "your-app-client-id"
gh secret set AZURE_CLIENT_SECRET --body "your-app-client-secret"
gh secret set AZURE_TENANT_ID --body "your-tenant-id"
```

---

## Entitlements (macOS)

The `electron/entitlements.plist` file defines the permissions required by the app:

- **Hardened Runtime**: Required for notarization
- **Network Access**: For backend communication
- **File Access**: For user data and projects
- **Device Access**: For future features (camera, microphone)

Do NOT add more entitlements than necessary, as this increases security risk.

---

## Testing Code Signing

### Local Testing (macOS)

```bash
# Build and sign locally
export CSC_LINK=/path/to/certificate.p12
export CSC_KEY_PASSWORD=your_password
npm run build:desktop

# Verify signing
codesign -dvv release/mac-arm64/Ashwen.app
```

### Local Testing (Windows)

```powershell
# Build and sign locally
$env:WIN_CSC_LINK = "C:\path\to\certificate.pfx"
$env:WIN_CSC_KEY_PASSWORD = "your_password"
npm run build:desktop

# Verify signing
Get-AuthenticodeSignature release\Ashwen.exe
```

### CI Testing

Use the `skip_signing` input to test builds without signing:

```yaml
# Manual trigger without signing
workflow_dispatch:
  inputs:
    skip_signing:
      description: 'Skip code signing (for testing)'
      default: false
```

---

## Troubleshooting

### macOS

**"The signature of the binary is invalid"**
- Ensure hardened runtime is enabled in entitlements
- Check that all dependencies are properly signed

**"Notarization failed"**
- Verify APPLE_ID and APPLE_APP_SPECIFIC_PASSWORD
- Check that the certificate is valid and not expired
- Review the notarization log in App Store Connect

**"The app is damaged and can't be opened"**
- This indicates a notarization or stapling failure
- Check the notarization status: `spctl -a -vv /path/to/app.app`

### Windows

**"Unknown Publisher"**
- EV certificate may not be properly installed
- Check that WIN_CSC_LINK points to a valid .pfx file
- Verify the certificate is not expired

**SmartScreen warning**
- EV certificates should immediately be trusted
- Standard certificates require "reputation" buildup
- Consider EV for production releases

---

## Security Best Practices

1. **Never commit certificates** to the repository
2. **Use GitHub Secrets** for all sensitive values
3. **Rotate secrets** if they may have been compromised
4. **Use EV certificates** for Windows production releases
5. **Enable 2FA** on your Apple Developer and CA accounts
6. **Audit access** to GitHub repository secrets

---

## Files Reference

| File | Purpose |
|------|---------|
| `electron/entitlements.plist` | macOS hardened runtime permissions |
| `electron-builder.yml` | Electron builder configuration |
| `.github/workflows/release.yml` | CI/CD pipeline with signing |
| `scripts/notarize.js` | Apple notarization automation |
