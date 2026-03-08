# GitHub Secrets Setup for Ashwen Desktop
# Run this script from the repository root

param(
    [switch]$MacOS,
    [switch]$WindowsPFX,
    [switch]$WindowsDigiCert,
    [switch]$WindowsSectigo,
    [switch]$WindowsAzure,
    [switch]$ListOnly
)

$ErrorActionPreference = "Stop"

Write-Host "Ashwen Desktop - GitHub Secrets Setup" -ForegroundColor Cyan
Write-Host ""

# Verify GitHub CLI
if (-not (Get-Command "gh" -ErrorAction SilentlyContinue)) {
    Write-Host "Error: GitHub CLI not installed. Install from https://cli.github.com/" -ForegroundColor Red
    exit 1
}

# List current secrets if requested
if ($ListOnly) {
    Write-Host "Current GitHub secrets:" -ForegroundColor Yellow
    gh secret list
    exit 0
}

# Helper function to set a secret
function Set-GitHubSecret {
    param([string]$Name, [string]$Prompt)
    
    Write-Host "$Prompt" -ForegroundColor Yellow
    $value = Read-Host "Enter value (or press Enter to skip)"
    
    if ($value) {
        $value | gh secret set $Name
        Write-Host "Secret '$Name' set successfully." -ForegroundColor Green
    } else {
        Write-Host "Skipped '$Name'." -ForegroundColor Gray
    }
}

# macOS secrets
if ($MacOS) {
    Write-Host "`n=== macOS Code Signing Secrets ===" -ForegroundColor Cyan
    
    Write-Host @"

For APPLE_CERTIFICATE_BASE64:
  1. Export your Developer ID Application certificate as .p12 from Keychain Access
  2. Run: base64 -i certificate.p12 | pbcopy (on Mac)
     Or on Windows: [Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.p12"))

"@ -ForegroundColor Gray
    
    Set-GitHubSecret -Name "APPLE_CERTIFICATE_BASE64" -Prompt "Base64-encoded .p12 certificate"
    Set-GitHubSecret -Name "APPLE_CERTIFICATE_PASSWORD" -Prompt "Password for the .p12 file"
    Set-GitHubSecret -Name "APPLE_ID" -Prompt "Your Apple Developer email"
    Set-GitHubSecret -Name "APPLE_APP_SPECIFIC_PASSWORD" -Prompt "App-specific password from appleid.apple.com"
    Set-GitHubSecret -Name "APPLE_TEAM_ID" -Prompt "10-character Team ID"
}

# Windows PFX secrets
if ($WindowsPFX) {
    Write-Host "`n=== Windows PFX Code Signing Secrets ===" -ForegroundColor Cyan
    
    Set-GitHubSecret -Name "WIN_EV_CERTIFICATE_BASE64" -Prompt "Base64-encoded PFX certificate"
    Set-GitHubSecret -Name "WIN_EV_CERTIFICATE_PASSWORD" -Prompt "Password for the PFX file"
}

# DigiCert secrets
if ($WindowsDigiCert) {
    Write-Host "`n=== DigiCert eSigner Secrets ===" -ForegroundColor Cyan
    
    "digicert" | gh secret set CLOUD_SIGNING_SERVICE
    Write-Host "Set CLOUD_SIGNING_SERVICE to 'digicert'" -ForegroundColor Green
    
    Set-GitHubSecret -Name "DIGICERT_USERNAME" -Prompt "DigiCert account email"
    Set-GitHubSecret -Name "DIGICERT_PASSWORD" -Prompt "DigiCert password"
    Set-GitHubSecret -Name "DIGICERT_API_KEY" -Prompt "DigiCert API key"
    Set-GitHubSecret -Name "DIGICERT_OTP_SECRET" -Prompt "TOTP secret (base32)"
    Set-GitHubSecret -Name "CLOUD_CERT_ALIAS" -Prompt "Certificate alias"
}

# Sectigo secrets
if ($WindowsSectigo) {
    Write-Host "`n=== Sectigo/SSL.com CodeSigner Secrets ===" -ForegroundColor Cyan
    
    "sectigo" | gh secret set CLOUD_SIGNING_SERVICE
    Write-Host "Set CLOUD_SIGNING_SERVICE to 'sectigo'" -ForegroundColor Green
    
    Set-GitHubSecret -Name "SECTIGO_USERNAME" -Prompt "SSL.com account email"
    Set-GitHubSecret -Name "SECTIGO_PASSWORD" -Prompt "SSL.com password"
    Set-GitHubSecret -Name "SECTIGO_CLIENT_ID" -Prompt "OAuth client ID"
    Set-GitHubSecret -Name "SECTIGO_CLIENT_SECRET" -Prompt "OAuth client secret"
    Set-GitHubSecret -Name "CLOUD_CREDENTIAL_ID" -Prompt "Credential ID"
}

# Azure secrets
if ($WindowsAzure) {
    Write-Host "`n=== Azure Key Vault Code Signing Secrets ===" -ForegroundColor Cyan
    
    "azure" | gh secret set CLOUD_SIGNING_SERVICE
    Write-Host "Set CLOUD_SIGNING_SERVICE to 'azure'" -ForegroundColor Green
    
    Set-GitHubSecret -Name "AZURE_KEY_VAULT_URL" -Prompt "Key Vault URL"
    Set-GitHubSecret -Name "AZURE_CERTIFICATE_NAME" -Prompt "Certificate name"
    Set-GitHubSecret -Name "AZURE_CLIENT_ID" -Prompt "Azure AD App client ID"
    Set-GitHubSecret -Name "AZURE_CLIENT_SECRET" -Prompt "Azure AD App client secret"
    Set-GitHubSecret -Name "AZURE_TENANT_ID" -Prompt "Azure AD tenant ID"
}

# Show usage if no options
if (-not ($MacOS -or $WindowsPFX -or $WindowsDigiCert -or $WindowsSectigo -or $WindowsAzure -or $ListOnly)) {
    Write-Host @"

Usage:
  .\scripts\setup-secrets-simple.ps1 -ListOnly              # List current secrets
  .\scripts\setup-secrets-simple.ps1 -MacOS                 # Setup macOS signing
  .\scripts\setup-secrets-simple.ps1 -WindowsPFX            # Setup Windows PFX signing
  .\scripts\setup-secrets-simple.ps1 -WindowsDigiCert       # Setup DigiCert eSigner
  .\scripts\setup-secrets-simple.ps1 -WindowsSectigo        # Setup Sectigo/SSL.com
  .\scripts\setup-secrets-simple.ps1 -WindowsAzure          # Setup Azure Key Vault

You can combine options:
  .\scripts\setup-secrets-simple.ps1 -MacOS -WindowsPFX     # Setup both platforms

"@ -ForegroundColor Yellow
}

Write-Host "`nCurrent secrets:" -ForegroundColor Cyan
gh secret list

Write-Host @"

Next steps:
  - To trigger a release: git tag v1.0.0 && git push origin v1.0.0
  - To skip signing in CI: use skip_signing=true workflow input

"@ -ForegroundColor Green
