#!/bin/bash
#
# GitHub Secrets Setup Script for Ashwen Desktop
# 
# This script helps you configure all required GitHub secrets for code signing.
# Run this script after pushing your repository to GitHub.
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Repository pushed to GitHub with remote named 'origin'
#
# Usage:
#   ./scripts/setup-github-secrets.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Ashwen Desktop - GitHub Secrets Setup${NC}"
echo -e "${BLUE}======================================${NC}"
echo

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed.${NC}"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub CLI.${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

# Check if repository has a remote
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo -e "${RED}Error: No GitHub repository found.${NC}"
    echo "Please ensure you have a git remote named 'origin' pointing to GitHub."
    exit 1
fi

echo -e "${GREEN}Repository: $REPO${NC}"
echo

# Function to set a secret with confirmation
set_secret() {
    local secret_name=$1
    local description=$2
    local is_required=$3
    
    echo -e "${YELLOW}Setting: $secret_name${NC}"
    echo -e "  Description: $description"
    echo -e "  Required: $is_required"
    echo
    
    if [ "$is_required" = "Yes" ]; then
        read -p "Enter value for $secret_name: " -s value
        echo
        if [ -z "$value" ]; then
            echo -e "${RED}Error: $secret_name is required but no value was provided.${NC}"
            return 1
        fi
        echo "$value" | gh secret set "$secret_name"
    else
        read -p "Enter value for $secret_name (leave empty to skip): " -s value
        echo
        if [ -n "$value" ]; then
            echo "$value" | gh secret set "$secret_name"
            echo -e "${GREEN}  ✓ Set${NC}"
        else
            echo -e "${YELLOW}  ⊘ Skipped${NC}"
        fi
    fi
    echo
}

# Function to set secret from file
set_secret_from_file() {
    local secret_name=$1
    local file_path=$2
    
    if [ -f "$file_path" ]; then
        gh secret set "$secret_name" < "$file_path"
        echo -e "${GREEN}  ✓ Set $secret_name from $file_path${NC}"
    else
        echo -e "${RED}  ✗ File not found: $file_path${NC}"
        return 1
    fi
}

echo -e "${BLUE}=== macOS Code Signing Secrets ===${NC}"
echo "These secrets are required for macOS code signing and notarization."
echo

echo -e "${YELLOW}Do you want to configure macOS code signing? (y/n)${NC}"
read -p "> " configure_mac
echo

if [ "$configure_mac" = "y" ] || [ "$configure_mac" = "Y" ]; then
    echo -e "${BLUE}--- APPLE_CERTIFICATE_BASE64 ---${NC}"
    echo "This is your Developer ID Application certificate exported as .p12 and base64 encoded."
    echo
    echo "To create this:"
    echo "  1. Open Keychain Access on Mac"
    echo "  2. Export your 'Developer ID Application' certificate as .p12"
    echo "  3. Run: base64 -i certificate.p12 | pbcopy"
    echo
    read -p "Paste the base64-encoded certificate: " -s cert_b64
    echo
    if [ -n "$cert_b64" ]; then
        echo "$cert_b64" | gh secret set APPLE_CERTIFICATE_BASE64
        echo -e "${GREEN}  ✓ APPLE_CERTIFICATE_BASE64 set${NC}"
    fi
    echo
    
    set_secret "APPLE_CERTIFICATE_PASSWORD" "Password used when exporting .p12 certificate" "Yes"
    set_secret "APPLE_ID" "Your Apple Developer account email" "Yes"
    set_secret "APPLE_APP_SPECIFIC_PASSWORD" "App-specific password from appleid.apple.com" "Yes"
    set_secret "APPLE_TEAM_ID" "10-character Team ID from developer.apple.com" "Yes"
fi

echo
echo -e "${BLUE}=== Windows Code Signing Secrets ===${NC}"
echo "These secrets are required for Windows code signing."
echo

echo -e "${YELLOW}Which Windows signing method do you want to use?${NC}"
echo "  1) PFX Certificate (traditional)"
echo "  2) DigiCert eSigner (cloud)"
echo "  3) Sectigo/SSL.com CodeSigner (cloud)"
echo "  4) Azure Key Vault (cloud)"
echo "  5) Skip Windows signing"
read -p "> " win_method
echo

case $win_method in
    1)
        echo -e "${BLUE}--- Traditional PFX Certificate ---${NC}"
        echo
        echo "To create the base64-encoded certificate:"
        echo "  PowerShell: [Convert]::ToBase64String([IO.File]::ReadAllBytes(\"certificate.pfx\")) | Out-File cert_b64.txt"
        echo "  Linux/Mac: base64 -i certificate.pfx -o cert_b64.txt"
        echo
        read -p "Paste the base64-encoded PFX certificate: " -s cert_b64
        echo
        if [ -n "$cert_b64" ]; then
            echo "$cert_b64" | gh secret set WIN_EV_CERTIFICATE_BASE64
            echo -e "${GREEN}  ✓ WIN_EV_CERTIFICATE_BASE64 set${NC}"
        fi
        echo
        set_secret "WIN_EV_CERTIFICATE_PASSWORD" "Password for the PFX file" "Yes"
        ;;
    2)
        echo -e "${BLUE}--- DigiCert eSigner ---${NC}"
        echo "Set CLOUD_SIGNING_SERVICE to 'digicert'"
        echo "digicert" | gh secret set CLOUD_SIGNING_SERVICE
        set_secret "DIGICERT_USERNAME" "DigiCert account email" "Yes"
        set_secret "DIGICERT_PASSWORD" "DigiCert account password" "Yes"
        set_secret "DIGICERT_API_KEY" "API key from DigiCert" "Yes"
        set_secret "DIGICERT_OTP_SECRET" "TOTP secret for 2FA (base32 encoded)" "Yes"
        set_secret "CLOUD_CERT_ALIAS" "Certificate alias from eSigner dashboard" "Yes"
        ;;
    3)
        echo -e "${BLUE}--- Sectigo/SSL.com CodeSigner ---${NC}"
        echo "Set CLOUD_SIGNING_SERVICE to 'sectigo'"
        echo "sectigo" | gh secret set CLOUD_SIGNING_SERVICE
        set_secret "SECTIGO_USERNAME" "SSL.com account email" "Yes"
        set_secret "SECTIGO_PASSWORD" "SSL.com account password" "Yes"
        set_secret "SECTIGO_CLIENT_ID" "OAuth client ID" "Yes"
        set_secret "SECTIGO_CLIENT_SECRET" "OAuth client secret" "Yes"
        set_secret "CLOUD_CREDENTIAL_ID" "Credential ID from dashboard" "Yes"
        ;;
    4)
        echo -e "${BLUE}--- Azure Key Vault ---${NC}"
        echo "Set CLOUD_SIGNING_SERVICE to 'azure'"
        echo "azure" | gh secret set CLOUD_SIGNING_SERVICE
        set_secret "AZURE_KEY_VAULT_URL" "Key Vault URL (e.g., https://vault.vault.azure.net/)" "Yes"
        set_secret "AZURE_CERTIFICATE_NAME" "Name of the certificate in Key Vault" "Yes"
        set_secret "AZURE_CLIENT_ID" "Azure AD App client ID" "Yes"
        set_secret "AZURE_CLIENT_SECRET" "Azure AD App client secret" "Yes"
        set_secret "AZURE_TENANT_ID" "Azure AD tenant ID" "Yes"
        ;;
    5)
        echo -e "${YELLOW}Skipping Windows code signing configuration.${NC}"
        ;;
    *)
        echo -e "${RED}Invalid option.${NC}"
        ;;
esac

echo
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Configuration Complete!${NC}"
echo -e "${BLUE}======================================${NC}"
echo
echo "Configured secrets:"
gh secret list
echo
echo -e "${YELLOW}Important reminders:${NC}"
echo "  - Never commit certificates or passwords to the repository"
echo "  - Rotate secrets if they may have been compromised"
echo "  - Use the 'skip_signing' workflow input for testing builds without signing"
echo
echo -e "${GREEN}You can now trigger a release build by pushing a tag:${NC}"
echo "  git tag v1.0.0"
echo "  git push origin v1.0.0"
