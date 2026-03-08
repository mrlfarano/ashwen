# Windows EV Code Signing Certificate Purchase Guide

This guide walks you through purchasing and setting up an EV (Extended Validation) code signing certificate for Ashwen Desktop.

## Why EV Code Signing?

| Feature | Standard Code Signing | EV Code Signing |
|---------|----------------------|-----------------|
| Immediate SmartScreen Trust | ❌ No (requires reputation) | ✅ Yes |
| Microsoft Verified | ❌ No | ✅ Yes |
| Organization Validation | Basic | Extended (rigorous) |
| Hardware Token | Optional | Required (or cloud HSM) |
| Cost | $100-200/year | $200-500/year |

**Recommendation**: Get EV code signing for immediate SmartScreen trust on Windows.

---

## Step 1: Choose a Certificate Authority (CA)

### Recommended CAs

| CA | Price (Est.) | Hardware Token | Cloud Signing | Notes |
|----|-------------|----------------|---------------|-------|
| **DigiCert** | $400-500/year | ✅ | ✅ | Premium, fast issuance, excellent support |
| **Sectigo** | $250-350/year | ✅ | ✅ | Good value, widely trusted |
| **GlobalSign** | $300-400/year | ✅ | ✅ | Good reputation |
| **SSL.com** | $200-300/year | ✅ | ✅ | Budget option |
| **ScrewDriver** | $200-300/year | ✅ | ❌ | Budget, USB token required |

**Recommendation**: **DigiCert** or **Sectigo** for best balance of price, trust, and cloud signing support.

### Cloud Signing vs Hardware Token

- **Cloud Signing (Recommended for CI/CD)**: Certificate stored in CA's HSM, sign via API
- **Hardware Token (USB)**: Physical USB device required for each signing operation

For GitHub Actions CI/CD, **cloud signing** is strongly recommended as it doesn't require physical hardware access during builds.

---

## Step 2: Prepare Required Information

Before starting the application, gather:

### Organization Information
- [ ] Legal business name (exactly as registered)
- [ ] Doing Business As (DBA) name if applicable
- [ ] Business registration number / Tax ID
- [ ] Incorporation date and jurisdiction
- [ ] Registered business address (no PO boxes)

### Contact Information
- [ ] Authorized representative's full name
- [ ] Job title
- [ ] Email address (business domain, not personal)
- [ ] Phone number (business line)

### Verification Documents
- [ ] Articles of Incorporation OR Certificate of Formation
- [ ] Business license (if required in your jurisdiction)
- [ ] Recent utility bill or bank statement (address proof)
- [ ] Government-issued photo ID of authorized representative

### Technical Requirements
- [ ] Corporate email address (matching business domain)
- [ ] Ability to receive phone verification calls during business hours

---

## Step 3: Purchase Process

### DigiCert (Recommended)

1. **Visit**: https://www.digicert.com/signing/code-signing-certificates

2. **Select**: EV Code Signing Certificate

3. **Choose delivery method**:
   - **Cloud HSM** (recommended for CI/CD)
   - **USB Token** (if you need offline signing)

4. **Create account** with your business email

5. **Fill in organization details**:
   - Must match your registration documents exactly
   - Any discrepancies will delay verification

6. **Submit payment** (credit card or invoice)

7. **Verification begins** (typically 1-5 business days)

### Sectigo (Budget Alternative)

1. **Visit**: https://sectigo.com/ssl-certificates-tls/code-signing

2. **Select**: EV Code Signing Certificate

3. **Choose eSigner** (cloud signing) option

4. **Follow application process**

---

## Step 4: Verification Process

The CA will verify:

### Organization Validation
- ✅ Business exists and is legally registered
- ✅ Business is in good standing
- ✅ Address is verified
- ✅ Phone number is verified

### Extended Validation
- ✅ Organization is legitimate (not a shell company)
- ✅ Authorized representative is employed by the organization
- ✅ Representative has authority to request certificates

### Verification Timeline
| CA | Typical Timeline |
|----|-----------------|
| DigiCert | 1-3 business days |
| Sectigo | 2-5 business days |
| GlobalSign | 3-5 business days |
| SSL.com | 1-3 business days |

**Note**: Delays occur if documents are incomplete or don't match. Double-check everything!

---

## Step 5: Receive and Export Certificate

### Option A: Cloud Signing (eSigner/DigiCert ONE)

1. Receive credentials from CA
2. Set up authentication (TOTP recommended)
3. Configure GitHub Actions with provided secrets:

```yaml
# Add to GitHub repository secrets
CLOUD_SIGNING_CLIENT_ID: <from CA>
CLOUD_SIGNING_CLIENT_SECRET: <from CA>
CLOUD_SIGNING_TOTP_SECRET: <TOTP secret>
CLOUD_SIGNING_CREDENTIAL_ID: <credential ID>
```

4. Update `.github/workflows/release.yml` to use cloud signing API

### Option B: Hardware Token → Export to PFX

1. Receive USB token by mail
2. Install on a Windows machine
3. Export certificate to PFX:

```powershell
# List certificates
certmgr.msc

# Export to PFX (right-click certificate → All Tasks → Export)
# - Yes, export the private key
# - PFX format
# - Set strong password
# - Save as ev-code-signing.pfx
```

4. Base64 encode for GitHub Actions:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("ev-code-signing.pfx")) | Out-File certificate_base64.txt
```

5. Add to GitHub repository secrets:

```bash
gh secret set WIN_EV_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set WIN_EV_CERTIFICATE_PASSWORD --body "your-strong-password"
```

---

## Step 6: Configure GitHub Actions

### For PFX Certificate

The existing workflow at `.github/workflows/release.yml` is already configured. Add secrets:

```bash
gh secret set WIN_EV_CERTIFICATE_BASE64 < certificate_base64.txt
gh secret set WIN_EV_CERTIFICATE_PASSWORD
```

### For Cloud Signing (DigiCert eSigner)

Update the workflow to use the CodeSignTool:

```yaml
# Add to workflow
- name: Install CodeSignTool
  run: |
    curl -L -o codesigntool.zip https://www.digicert.com/ssl/utilities/CodeSignTool.zip
    unzip codesigntool.zip -d codesigntool

- name: Sign with DigiCert eSigner
  env:
    CLOUD_SIGNING_CLIENT_ID: ${{ secrets.CLOUD_SIGNING_CLIENT_ID }}
    CLOUD_SIGNING_CLIENT_SECRET: ${{ secrets.CLOUD_SIGNING_CLIENT_SECRET }}
    CLOUD_SIGNING_TOTP_SECRET: ${{ secrets.CLOUD_SIGNING_TOTP_SECRET }}
    CLOUD_SIGNING_CREDENTIAL_ID: ${{ secrets.CLOUD_SIGNING_CREDENTIAL_ID }}
  run: |
    ./codesigntool/CodeSignTool.sh sign \
      -input_file_path=release/Ashwen.exe \
      -output_dir_path=release/signed \
      -credential_id=$CLOUD_SIGNING_CREDENTIAL_ID \
      -client_id=$CLOUD_SIGNING_CLIENT_ID \
      -client_secret=$CLOUD_SIGNING_CLIENT_SECRET \
      -totp_secret=$CLOUD_SIGNING_TOTP_SECRET
```

---

## Cost Breakdown

| Item | Cost | Frequency |
|------|------|-----------|
| EV Code Signing Certificate | $200-500 | Per year |
| Business registration (if needed) | $50-500 | One-time |
| USB token shipping (if applicable) | $10-30 | Per issuance |
| **Total First Year** | **$260-1030** | |

---

## Checklist

Before starting:
- [ ] Business is legally registered
- [ ] Have incorporation documents ready
- [ ] Have business address proof ready
- [ ] Have authorized representative's ID ready
- [ ] Choose CA (recommend: DigiCert or Sectigo)
- [ ] Choose delivery method (recommend: Cloud signing)
- [ ] Budget approved ($200-500)

After receiving certificate:
- [ ] Export certificate to PFX (if hardware token)
- [ ] Base64 encode certificate
- [ ] Add `WIN_EV_CERTIFICATE_BASE64` to GitHub secrets
- [ ] Add `WIN_EV_CERTIFICATE_PASSWORD` to GitHub secrets
- [ ] Test signing in CI/CD

---

## Support Contacts

| CA | Support |
|----|---------|
| DigiCert | https://www.digicert.com/support |
| Sectigo | https://sectigo.com/support |
| GlobalSign | https://www.globalsign.com/en/support |
| SSL.com | https://www.ssl.com/support |

---

## Next Steps

1. Complete certificate purchase and verification
2. Add secrets to GitHub repository
3. Test build with `skip_signing: false`
4. Verify SmartScreen shows "Ashwen" as verified publisher

Once complete, update the checklist in this document and notify the team.
