#
# GitHub Secrets Setup Script for Ashwen Desktop (PowerShell version)
# 
# This script helps you configure all required GitHub secrets for code signing.
# Run this script after pushing your repository to GitHub.
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - Repository pushed to GitHub with remote named 'origin'
#
# Usage:
#   .\scripts\setup-github-secrets.ps1
#

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Blue
Write-Host "Ashwen Desktop - GitHub Secrets Setup" -ForegroundColor Blue
Write-Host "======================================" -ForegroundColor Blue
Write-Host ""

# Check if gh is installed
if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: GitHub CLI (gh) is not installed." -ForegroundColor Red
    Write-Host "Please install it from: https://cli.github.com/"
    exit 1
}

# Check if authenticated to github.com
$authStatus = gh auth status -h github.com 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Not authenticated with GitHub CLI for github.com." -ForegroundColor Red
    Write-Host "Please run: gh auth login -h github.com"
    exit 1
}

# Get repository info
$repo = gh repo view --json nameWithOwner -q .nameWithOwner 2>$null
if (-not $repo) {
    Write-Host "Error: No GitHub repository found." -ForegroundColor Red
    Write-Host "Please ensure you have a git remote named 'origin' pointing to GitHub."
    exit 1
}

Write-Host "Repository: $repo" -ForegroundColor Green
Write-Host ""

function Set-Secret {
    param(
        [string]$Name,
        [string]$Description,
        [bool]$Required
    )
    
    Write-Host "Setting: $Name" -ForegroundColor Yellow
    Write-Host "  Description: $Description"
    Write-Host "  Required: $Required"
    
    $value = Read-Host "Enter value for $Name"
    
    if ($Required -and [string]::IsNullOrEmpty($value)) {
        Write-Host "Error: $Name is required but no value was provided." -ForegroundColor Red
        return $false
    }
    
    if (-not [string]::IsNullOrEmpty($value)) {
        $value | gh secret set $Name
        Write-Host "  ✓ Set" -ForegroundColor Green
    } else {
        Write-Host "  ⊘ Skipped" -ForegroundColor Yellow
    }
    
    Write-Host ""
    return $true
}

# macOS Code Signing
Write-Host "=== macOS Code Signing Secrets ===" -ForegroundColor Blue
Write-Host "These secrets are required for macOS code signing and notarization."
Write-Host ""

$configureMac = Read-Host "Do you want to configure macOS code signing? (y/n)"

if ($configureMac -eq "y" -or $configureMac -eq "Y") {
    Write-Host "--- APPLE_CERTIFICATE_BASE64 ---" -ForegroundColor Blue
    Write-Host "This is your Developer ID Application certificate exported as .p12 and base64 encoded."
    Write-Host ""
    Write-Host "To create this:"
    Write-Host "  1. Open Keychain Access on Mac"
    Write-Host "  2. Export your 'Developer ID Application' certificate as .p12"
    Write-Host "  3. Run: base64 -i certificate.p12 | pbcopy"
    Write-Host ""
    
    $certB64 = Read-Host "Paste the base64-encoded certificate"
    if (-not [string]::IsNullOrEmpty($certB64)) {
        $certB64 | gh secret set APPLE_CERTIFICATE_BASE64
        Write-Host "  ✓ APPLE_CERTIFICATE_BASE64 set" -ForegroundColor Green
    }
    Write-Host ""
    
    Set-Secret -Name "APPLE_CERTIFICATE_PASSWORD" -Description "Password used when exporting .p12 certificate" -Required $true
    Set-Secret -Name "APPLE_ID" -Description "Your Apple Developer account email" -Required $true
    Set-Secret -Name "APPLE_APP_SPECIFIC_PASSWORD" -Description "App-specific password from appleid.apple.com" -Required $true
    Set-Secret -Name "APPLE_TEAM_ID" -Description "10-character Team ID from developer.apple.com" -Required $true
}

Write-Host ""
Write-Host "=== Windows Code Signing Secrets ===" -ForegroundColor Blue
Write-Host "These secrets are required for Windows code signing."
Write-Host ""

Write-Host "Which Windows signing method do you want to use?" -ForegroundColor Yellow
Write-Host "  1) PFX Certificate (traditional)"
Write-Host "  2) DigiCert eSigner (cloud)"
Write-Host "  3) Sectigo/SSL.com CodeSigner (cloud)"
Write-Host "  4) Azure Key Vault (cloud)"
Write-Host "  5) Skip Windows signing"
$winMethod = Read-Host "> "

switch ($winMethod) {
    "1" {
        Write-Host "--- Traditional PFX Certificate ---" -ForegroundColor Blue
        Write-Host ""
        Write-Host "To create the base64-encoded certificate:"
        Write-Host '  PowerShell: [Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx")) | Out-File cert_b64.txt'
        Write-Host "  Linux/Mac: base64 -i certificate.pfx -o cert_b64.txt"
        Write-Host ""
        
        $certB64 = Read-Host "Paste the base64-encoded PFX certificate"
        if (-not [string]::IsNullOrEmpty($certB64)) {
            $certB64 | gh secret set WIN_EV_CERTIFICATE_BASE64
            Write-Host "  ✓ WIN_EV_CERTIFICATE_BASE64 set" -ForegroundColor Green
        }
        Write-Host ""
        
        Set-Secret -Name "WIN_EV_CERTIFICATE_PASSWORD" -Description "Password for the PFX file" -Required $true
    }
    "2" {
        Write-Host "--- DigiCert eSigner ---" -ForegroundColor Blue
        "digicert" | gh secret set CLOUD_SIGNING_SERVICE
        Write-Host "Set CLOUD_SIGNING_SERVICE to 'digicert'"
        Set-Secret -Name "DIGICERT_USERNAME" -Description "DigiCert account email" -Required $true
        Set-Secret -Name "DIGICERT_PASSWORD" -Description "DigiCert account password" -Required $true
        Set-Secret -Name "DIGICERT_API_KEY" -Description "API key from DigiCert" -Required $true
        Set-Secret -Name "DIGICERT_OTP_SECRET" -Description "TOTP secret for 2FA (base32 encoded)" -Required $true
        Set-Secret -Name "CLOUD_CERT_ALIAS" -Description "Certificate alias from eSigner dashboard" -Required $true
    }
    "3" {
        Write-Host "--- Sectigo/SSL.com CodeSigner ---" -ForegroundColor Blue
        "sectigo" | gh secret set CLOUD_SIGNING_SERVICE
        Write-Host "Set CLOUD_SIGNING_SERVICE to 'sectigo'"
        Set-Secret -Name "SECTIGO_USERNAME" -Description "SSL.com account email" -Required $true
        Set-Secret -Name "SECTIGO_PASSWORD" -Description "SSL.com account password" -Required $true
        Set-Secret -Name "SECTIGO_CLIENT_ID" -Description "OAuth client ID" -Required $true
        Set-Secret -Name "SECTIGO_CLIENT_SECRET" -Description "OAuth client secret" -Required $true
        Set-Secret -Name "CLOUD_CREDENTIAL_ID" -Description "Credential ID from dashboard" -Required $true
    }
    "4" {
        Write-Host "--- Azure Key Vault ---" -ForegroundColor Blue
        "azure" | gh secret set CLOUD_SIGNING_SERVICE
        Write-Host "Set CLOUD_SIGNING_SERVICE to 'azure'"
        Set-Secret -Name "AZURE_KEY_VAULT_URL" -Description "Key Vault URL (e.g., https://vault.vault.azure.net)" -Required $true
        Set-Secret -Name "AZURE_CERTIFICATE_NAME" -Description "Name of the certificate in Key Vault" -Required $true
        Set-Secret -Name "AZURE_CLIENT_ID" -Description "Azure AD App client ID" -Required $true
        Set-Secret -Name "AZURE_CLIENT_SECRET" -Description "Azure AD App client secret" -Required $true
        Set-Secret -Name "AZURE_TENANT_ID" -Description "Azure AD tenant ID" -Required $true
    }
    "5" {
        Write-Host "Skipping Windows code signing configuration." -ForegroundColor Yellow
    }
    default {
        Write-Host "Invalid option." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Blue
Write-Host "Configuration Complete!" -ForegroundColor Blue
Write-Host "======================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Configured secrets:"
gh secret list
Write-Host ""
Write-Host "Important reminders:" -ForegroundColor Yellow
Write-Host "  - Never commit certificates or passwords to the repository"
Write-Host "  - Rotate secrets if they may have been compromised"
Write-Host "  - Use the 'skip_signing' workflow input for testing builds without signing"
Write-Host ""
Write-Host "You can now trigger a release build by pushing a tag:" -ForegroundColor Green
Write-Host "  git tag v1.0.0"
Write-Host "  git push origin v1.0.0"
