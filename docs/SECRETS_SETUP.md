# GitHub Secrets Setup Instructions

## Quick Start

The repository includes interactive scripts to configure GitHub secrets for code signing:

### On Windows:
```powershell
.\scripts\setup-secrets-simple.ps1 -MacOS           # For macOS signing
.\scripts\setup-secrets-simple.ps1 -WindowsPFX      # For Windows PFX signing
.\scripts\setup-secrets-simple.ps1 -WindowsDigiCert # For DigiCert cloud signing
.\scripts\setup-secrets-simple.ps1 -WindowsSectigo  # For SSL.com cloud signing
.\scripts\setup-secrets-simple.ps1 -WindowsAzure    # For Azure Key Vault signing
```

### On Linux/macOS:
```bash
./scripts/setup-github-secrets.sh
```

## Required Secrets by Platform

### macOS (Apple Developer)
| Secret | Description |
|--------|-------------|
| `APPLE_CERTIFICATE_BASE64` | Base64-encoded .p12 certificate |
| `APPLE_CERTIFICATE_PASSWORD` | Password for .p12 file |
| `APPLE_ID` | Apple Developer email |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password from appleid.apple.com |
| `APPLE_TEAM_ID` | 10-character Team ID |

### Windows - Traditional PFX
| Secret | Description |
|--------|-------------|
| `WIN_EV_CERTIFICATE_BASE64` | Base64-encoded .pfx certificate |
| `WIN_EV_CERTIFICATE_PASSWORD` | Password for .pfx file |

### Windows - DigiCert eSigner
| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to "digicert" |
| `DIGICERT_USERNAME` | DigiCert account email |
| `DIGICERT_PASSWORD` | DigiCert password |
| `DIGICERT_API_KEY` | API key from DigiCert |
| `DIGICERT_OTP_SECRET` | TOTP secret (base32) |
| `CLOUD_CERT_ALIAS` | Certificate alias |

### Windows - Sectigo/SSL.com
| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to "sectigo" |
| `SECTIGO_USERNAME` | SSL.com email |
| `SECTIGO_PASSWORD` | SSL.com password |
| `SECTIGO_CLIENT_ID` | OAuth client ID |
| `SECTIGO_CLIENT_SECRET` | OAuth client secret |
| `CLOUD_CREDENTIAL_ID` | Credential ID |

### Windows - Azure Key Vault
| Secret | Description |
|--------|-------------|
| `CLOUD_SIGNING_SERVICE` | Set to "azure" |
| `AZURE_KEY_VAULT_URL` | Key Vault URL |
| `AZURE_CERTIFICATE_NAME` | Certificate name |
| `AZURE_CLIENT_ID` | Azure AD App client ID |
| `AZURE_CLIENT_SECRET` | Azure AD App client secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |

## Manual Secret Setting

You can also set secrets directly using the GitHub CLI:

```bash
# Set a secret from a value
echo "your-value" | gh secret set SECRET_NAME

# Set a secret from a file
gh secret set SECRET_NAME < file.txt
```

## Verifying Secrets

To list currently configured secrets:
```bash
gh secret list
```

## Testing Without Signing

To test builds without code signing, use the `skip_signing` input when triggering the workflow:
- In GitHub Actions UI: Check "Skip code signing"
- Via API: Set `skip_signing: true`
