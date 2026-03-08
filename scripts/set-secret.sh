#!/bin/bash
#
# Quick GitHub Secret Setter
# Usage: ./scripts/set-secret.sh SECRET_NAME "secret value"
#
# Example:
#   ./scripts/set-secret.sh APPLE_ID "your-email@example.com"
#

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 SECRET_NAME \"secret value\""
    echo ""
    echo "Available secrets for macOS:"
    echo "  APPLE_CERTIFICATE_BASE64  - Base64-encoded .p12 certificate"
    echo "  APPLE_CERTIFICATE_PASSWORD - Password for .p12 file"
    echo "  APPLE_ID                  - Apple Developer email"
    echo "  APPLE_APP_SPECIFIC_PASSWORD - App-specific password"
    echo "  APPLE_TEAM_ID             - 10-character Team ID"
    echo ""
    echo "Available secrets for Windows (PFX):"
    echo "  WIN_EV_CERTIFICATE_BASE64 - Base64-encoded .pfx certificate"
    echo "  WIN_EV_CERTIFICATE_PASSWORD - Password for .pfx file"
    echo ""
    echo "Available secrets for DigiCert eSigner:"
    echo "  CLOUD_SIGNING_SERVICE     - Set to 'digicert'"
    echo "  DIGICERT_USERNAME         - DigiCert email"
    echo "  DIGICERT_PASSWORD         - DigiCert password"
    echo "  DIGICERT_API_KEY          - API key"
    echo "  DIGICERT_OTP_SECRET       - TOTP secret (base32)"
    echo "  CLOUD_CERT_ALIAS          - Certificate alias"
    echo ""
    echo "Available secrets for Sectigo/SSL.com:"
    echo "  CLOUD_SIGNING_SERVICE     - Set to 'sectigo'"
    echo "  SECTIGO_USERNAME          - SSL.com email"
    echo "  SECTIGO_PASSWORD          - SSL.com password"
    echo "  SECTIGO_CLIENT_ID         - OAuth client ID"
    echo "  SECTIGO_CLIENT_SECRET     - OAuth client secret"
    echo "  CLOUD_CREDENTIAL_ID       - Credential ID"
    echo ""
    echo "Available secrets for Azure Key Vault:"
    echo "  CLOUD_SIGNING_SERVICE     - Set to 'azure'"
    echo "  AZURE_KEY_VAULT_URL       - Key Vault URL"
    echo "  AZURE_CERTIFICATE_NAME    - Certificate name"
    echo "  AZURE_CLIENT_ID           - Azure AD App client ID"
    echo "  AZURE_CLIENT_SECRET       - Azure AD App client secret"
    echo "  AZURE_TENANT_ID           - Azure AD tenant ID"
    exit 1
fi

SECRET_NAME="$1"
SECRET_VALUE="$2"

echo "Setting secret: $SECRET_NAME"
echo "$SECRET_VALUE" | gh secret set "$SECRET_NAME"
echo "✓ Done"
