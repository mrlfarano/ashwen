# EV Code Signing Certificate - Purchase Checklist

> **Owner**: [Assign to the person responsible]
> **Due Date**: [Set target date]
> **Status**: 🔴 Not Started

---

## Pre-Purchase Checklist

- [ ] Business is legally registered (LLC, Corp, etc.)
- [ ] Have Articles of Incorporation or Certificate of Formation
- [ ] Have business license (if required in jurisdiction)
- [ ] Have utility bill or bank statement for address proof
- [ ] Have government-issued photo ID of authorized representative
- [ ] Business email on company domain available
- [ ] Business phone line available for verification
- [ ] Budget approved ($200-500)

## Certificate Selection

- [ ] Choose Certificate Authority:
  - [ ] DigiCert (~$400-500) - Premium option
  - [ ] Sectigo (~$250-350) - Good value
  - [ ] GlobalSign (~$300-400) - Good reputation
  - [ ] SSL.com (~$200-300) - Budget option

- [ ] Choose delivery method:
  - [ ] Cloud Signing (eSigner) - **Recommended for CI/CD**
  - [ ] USB Hardware Token - Required for offline signing

## Purchase Process

- [ ] Visit CA website
- [ ] Create account with business email
- [ ] Fill in organization details (EXACTLY as registered)
- [ ] Submit payment
- [ ] Receive order confirmation

## Verification Process

- [ ] Respond to CA verification emails promptly
- [ ] Provide requested documents
- [ ] Complete phone verification
- [ ] Wait for approval (1-5 business days)

## Certificate Setup

### Option A: Cloud Signing
- [ ] Receive credentials from CA
- [ ] Set up TOTP authentication
- [ ] Test signing with CodeSignTool

### Option B: Hardware Token
- [ ] Receive USB token by mail
- [ ] Install on Windows machine
- [ ] Test signing locally
- [ ] Export to PFX format
- [ ] Base64 encode the PFX file

## GitHub Actions Integration

- [ ] Add `WIN_EV_CERTIFICATE_BASE64` secret
- [ ] Add `WIN_EV_CERTIFICATE_PASSWORD` secret
- [ ] (Cloud signing) Add additional CA-specific secrets
- [ ] Update workflow if needed for cloud signing

## Verification

- [ ] Run release workflow with signing enabled
- [ ] Download signed Windows installer
- [ ] Verify signature shows "Ashwen" as publisher
- [ ] Verify no SmartScreen warning appears
- [ ] Document certificate expiration date

---

## Notes

- Certificate is valid for 1-3 years (set calendar reminder for renewal)
- Keep certificate password secure
- If using USB token, store it securely when not in use
- Cloud signing is easier for CI/CD but may have per-sign costs

## Certificate Information (Fill in after purchase)

| Field | Value |
|-------|-------|
| CA | |
| Order Number | |
| Certificate ID | |
| Issued Date | |
| Expiration Date | |
| Delivery Method | Cloud / USB |
