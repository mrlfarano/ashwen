# GitHub Secrets Configuration Guide

This guide provides step-by-step instructions for configuring GitHub repository secrets for code signing Ashwen Desktop.

## Quick Start

Once your repository is pushed to GitHub, run the interactive setup script:

```bash
./scripts/setup-github-secrets.sh
```

This script will guide you through configuring all required secrets.

---

## Manual Configuration

If you prefer to configure secrets manually, follow the steps below.

### Prerequisites

1. **GitHub CLI** installed (`gh`)
2. **Authenticated** with `gh auth login`
3. **Repository** pushed to GitHub

### Verify Setup

```bash
# Check authentication
gh auth status

# Check repository
gh repo view

# List current secrets
gh secret list
```

---

## Required Secrets

### macOS Code Signing (Required for Mac builds)

| Secret | Description | How to Obtain |
|--------|-------------|---------------|
| `APPLE_CERTIFICATE_BASE64` | Base64-encoded .p12 certificate | See steps below |
| `APPLE_CERTIFICATE_PASSWORD` | Password used when exporting .p12 | You set this during export |
| `APPLE_ID` | Your Apple Developer email | Your login email |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password | Generate at appleid.apple.com |
| `APPLE_TEAM_ID` | 10-character team identifier | Found in Developer Portal |

#### Step-by-Step: macOS Certificate Setup

1. **Export Certificate as .p12**
   ```bash
   # On your Mac:
   # 1. Open Keychain Access
   # 2. Find "Developer ID Application: Your Name (TEAMID)"
   # 3. Right-click → Export
   # 4. Save as certificate.p12 with a strong password
   ```

2. **Base64 Encode**
   ```bash
   base64 -i certificate.p12 -o certificate_base64.txt
   ```

3. **Set GitHub Secret**
   ```bash
   gh secret set APPLE_CERTIFICATE_BASE64 < certificate_base64.txt
   gh secret set APPLE_CERTIFICATE_PASSWORD
   # (paste your password when prompted)
   ```

4. **Create App-Specific Password**
   - Go to: https://appleid.apple.com/
   - Sign in → Security → App-Specific Passwords
   - Click "Generate Password"
   - Save it securely

   ```bash
   gh secret set APPLE_APP_SPECIFIC_PASSWORD
   # (paste the generated password)
   ```

5. **Get Team ID**
   - Go to: https://developer.apple.com/account
   - Click "Membership" in sidebar
   - Copy your Team ID

   ```bash
   gh secret set APPLE_TEAM_ID
   # (paste your Team ID)
   ```

6. **Set Apple ID**
   ```bash
   gh secret set APPLE_ID
   # (enter your Apple Developer email)
   ```

---

### Windows Code Signing (Required for Windows builds)

Choose **one** of the following methods:

#### Option A: Traditional PFX Certificate

| Secret | Description |
|--------|-------------|
| `WIN_EV_CERTIFICATE_BASE64` | Base64-encoded .pfx certificate |
| `WIN_EV_CERTIFICATE_PASSWORD` | Password for the .pfx file |

```powershell
# On Windows PowerShell:
[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx")) | Out-File certificate_base64.txt

# Set secrets:
gh secret set WIN_EV_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set WIN_EV_CERTIFICATE_PASSWORD
```

#### Option B: DigiCert eSigner (Cloud Signing)

| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to `digicert` |
| `DIGICERT_USERNAME` | DigiCert account email |
| `DIGICERT_PASSWORD` | DigiCert account password |
| `DIGICERT_API_KEY` | API key from DigiCert |
| `DIGICERT_OTP_SECRET` | TOTP secret (base32) |
| `CLOUD_CERT_ALIAS` | Certificate alias |

```bash
echo "digicert" | gh secret set CLOUD_SIGNING_SERVICE
gh secret set DIGICERT_USERNAME
gh secret set DIGICERT_PASSWORD
gh secret set DIGICERT_API_KEY
gh secret set DIGICERT_OTP_SECRET
gh secret set CLOUD_CERT_ALIAS
```

#### Option C: Sectigo/SSL.com CodeSigner (Cloud Signing)

| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to `sectigo` |
| `SECTIGO_USERNAME` | SSL.com account email |
| `SECTIGO_PASSWORD` | SSL.com account password |
| `SECTIGO_CLIENT_ID` | OAuth client ID |
| `SECTIGO_CLIENT_SECRET` | OAuth client secret |
| `CLOUD_CREDENTIAL_ID` | Credential ID |

```bash
echo "sectigo" | gh secret set CLOUD_SIGNING_SERVICE
gh secret set SECTIGO_USERNAME
gh secret set SECTIGO_PASSWORD
gh secret set SECTIGO_CLIENT_ID
gh secret set SECTIGO_CLIENT_SECRET
gh secret set CLOUD_CREDENTIAL_ID
```

#### Option D: Azure Key Vault (Cloud Signing)

| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to `azure` |
| `AZURE_KEY_VAULT_URL` | Key Vault URL |
| `AZURE_CERTIFICATE_NAME` | Certificate name |
| `AZURE_CLIENT_ID` | Azure AD App client ID |
| `AZURE_CLIENT_SECRET` | Azure AD App client secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |

```bash
echo "azure" | gh secret set CLOUD_SIGNING_SERVICE
gh secret set AZURE_KEY_VAULT_URL
gh secret set AZURE_CERTIFICATE_NAME
gh secret set AZURE_CLIENT_ID
gh secret set AZURE_CLIENT_SECRET
gh secret set AZURE_TENANT_ID
```

---

## Verification

After setting all secrets, verify the configuration:

```bash
gh secret list
```

Expected output for full configuration:
```
APPLE_APP_SPECIFIC_PASSWORD  Updated 2024-XX-XX
APPLE_CERTIFICATE_BASE64     Updated 2024-XX-XX
APPLE_CERTIFICATE_PASSWORD   Updated 2024-XX-XX
APPLE_ID                     Updated 2024-XX-XX
APPLE_TEAM_ID                Updated 2024-XX-XX
WIN_EV_CERTIFICATE_BASE64    Updated 2024-XX-XX
WIN_EV_CERTIFICATE_PASSWORD  Updated 2024-XX-XX
```

---

## Testing Without Signing

To test builds without code signing, use the workflow dispatch input:

1. Go to Actions → Release Desktop App
2. Click "Run workflow"
3. Check "Skip code signing (for testing)"
4. Click "Run workflow"

Or trigger via CLI:
```bash
gh workflow run release.yml -f skip_signing=true
```

---

## Troubleshooting

### "secret not found" in workflow logs
- Verify the secret is set: `gh secret list`
- Secret names are case-sensitive
- Ensure you're setting secrets on the correct repository

### Certificate import fails
- Verify the base64 encoding is correct
- Check that the certificate password is correct
- Ensure the certificate hasn't expired

### Notarization fails (macOS)
- Verify `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, and `APPLE_TEAM_ID`
- Ensure app-specific password is still valid
- Check Apple Developer account is in good standing

### Windows signing fails
- Verify certificate is EV (Extended Validation) for immediate trust
- Check timestamp servers are accessible
- Ensure certificate hasn't expired

---

## Security Best Practices

1. **Never commit** certificates or passwords to the repository
2. **Use strong passwords** for certificate exports
3. **Rotate secrets** periodically (every 6-12 months)
4. **Limit repository access** to trusted collaborators only
5. **Enable 2FA** on all accounts (Apple, GitHub, CA)
6. **Monitor workflow logs** for accidental secret exposure
7. **Review repository access** regularly

---

## Quick Reference: Setting All Secrets via CLI

```bash
# macOS
gh secret set APPLE_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set APPLE_CERTIFICATE_PASSWORD
gh secret set APPLE_ID
gh secret set APPLE_APP_SPECIFIC_PASSWORD
gh secret set APPLE_TEAM_ID

# Windows (PFX)
gh secret set WIN_EV_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set WIN_EV_CERTIFICATE_PASSWORD
```

---

## Next Steps

After configuring secrets:

1. **Test the workflow** with `skip_signing=true`
2. **Create a release** by pushing a tag: `git tag v1.0.0 && git push origin v1.0.0`
3. **Verify signing** by checking the release artifacts
4. **Test on target platforms** to ensure proper signing

For more information, see [CODE_SIGNING.md](./CODE_SIGNING.md).
