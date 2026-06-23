# Backblaze B2 Setup Guide for ResticLVM

This guide walks through setting up Backblaze B2 cloud storage as a backup destination for ResticLVM.

## Why B2?

- **Cost-effective**: $0.005/GB/month storage, free tier available (10 GB)
- **S3-compatible**: Works with restic's mature S3 backend
- **Reliable**: Geographic redundancy, 99.9% durability SLA
- **No egress fees**: First 1GB/day download is free

## Important: Use S3-Compatible API

Per restic documentation, **use B2's S3-compatible API** instead of the native B2 API:

> Due to issues with error handling in the current B2 library that restic uses, the recommended way to utilize Backblaze B2 is by using its S3-compatible API.

**What this means:**
- ✅ Use: `s3:s3.region.backblazeb2.com/bucket/path`
- ❌ Avoid: `b2:bucket:path` (supported but not recommended)

---

## Step 1: Create Backblaze Account

1. Go to https://www.backblaze.com/b2/sign-up.html
2. Sign up for free account (no credit card required for free tier)
3. Verify email and complete registration

**Free tier includes:**
- 10 GB storage
- 1 GB/day download bandwidth
- Unlimited uploads

---

## Step 2: Create B2 Bucket

1. Log into B2 Console
2. Navigate to **B2 Cloud Storage** → **Buckets** → **Create a Bucket**
3. Configure:
   - **Bucket Name**: Choose globally unique name (e.g., `mycompany-backups-prod`)
   - **Files in Bucket**: **Private** (recommended)
   - **Default Encryption**: **Disabled** (restic encrypts data)
   - **Object Lock**: **Disabled** (not needed for restic)
4. Click **Create a Bucket**
5. **Note the bucket region** (e.g., `us-west-004`, `eu-central-003`) - you'll need this!

---

## Step 3: Configure Lifecycle Rule (CRITICAL!)

**This step is mandatory to avoid runaway costs!**

### Why This Matters

When restic prunes old snapshots, it deletes files from B2. However, B2 **keeps all file versions by default**, including deleted ones. Without a lifecycle rule:

- ❌ Deleted files still consume storage
- ❌ You pay for data you can't see
- ❌ Storage costs grow indefinitely
- ❌ No way to recover storage space

With lifecycle rule enabled:

- ✅ Old file versions auto-deleted after 1 day
- ✅ Storage space actually freed
- ✅ Costs stay predictable
- ✅ Only current data is stored

### Setup Instructions

1. Click on your bucket name to open bucket settings
2. Find **Lifecycle Settings** section
3. Click **Add a New Lifecycle Rule** or similar button
4. Select: **"Keep only the last version of the file"**
5. Apply to: **All files** (or specific prefix if desired)
6. Save the rule

### Verification

After saving, your bucket details should show:
```
File Lifecycle: Keep only the last version
```

If it still says "Keep all versions", the rule wasn't applied correctly.

---

## Step 4: Create S3-Compatible Application Key

**Important**: You must create an **S3-compatible** key, not a regular B2 key!

### Instructions

1. Go to **App Keys** → **Add a New Application Key**
2. Configure:
   - **Name of Key**: `resticlvm-s3-backup` (or similar descriptive name)
   - **⚠️ CRITICAL: Check "S3 Compatible" checkbox!**
   - **Allow access to Bucket(s)**: Select your specific bucket (more secure than "All")
   - **Type of Access**: **Read and Write**
   - **File name prefix**: Leave empty (or use prefix like `resticlvm/`)
   - **Duration**: No limit (or set expiration for security)
3. Click **Create New Key**

### Save Credentials Immediately!

The key is shown **only once**. Save these values:

```
keyID:          004xyz...       → This is your AWS_ACCESS_KEY_ID
applicationKey: K004abc...      → This is your AWS_SECRET_ACCESS_KEY
```

**Security Note**: Store these securely. Anyone with these credentials can access your bucket!

---

## Step 5: Store Credentials Securely on Backup Server

### Create Credential File

```bash
# Create secure directory (as root)
sudo mkdir -p /root/.config/resticlvm
sudo chmod 700 /root/.config/resticlvm

# Store B2 credentials
sudo tee /root/.config/resticlvm/b2-env << 'EOF'
export AWS_ACCESS_KEY_ID="your-key-id-here"
export AWS_SECRET_ACCESS_KEY="your-application-key-here"
EOF

# Secure the file (root read-only)
sudo chmod 600 /root/.config/resticlvm/b2-env
```

### Verify Credentials

```bash
# Confirm both credentials load, without printing their values
sudo bash -c 'source /root/.config/resticlvm/b2-env && [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ] && echo "B2 credentials loaded"'
```

You should see your key ID printed.

---

## Step 6: Initialize Restic Repository in B2

### Manual Initialization (Recommended)

Before using ResticLVM, initialize the repository manually to verify credentials work:

```bash
# Source credentials
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  restic -r s3:s3.REGION.backblazeb2.com/BUCKET-NAME/PREFIX \
  init --password-file /path/to/restic-password.txt'
```

**Replace:**
- `REGION`: Your bucket region (e.g., `us-west-004`)
- `BUCKET-NAME`: Your bucket name
- `PREFIX`: Path within bucket (e.g., `resticlvm/root`)

**Example:**
```bash
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  restic -r s3:s3.us-west-004.backblazeb2.com/mycompany-backups/resticlvm/root \
  init --password-file /etc/resticlvm/restic-password.txt'
```

**Expected output:**
```
created restic repository abc123def at s3:s3.us-west-004...
```

---

## Step 7: Configure ResticLVM

### Example: Direct B2 Backup

```toml
# /etc/resticlvm/backup.toml

[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys", "/tmp"]

[[logical_volume_root.root.repositories]]
repo_path = "s3:s3.us-west-004.backblazeb2.com/mycompany-backups/resticlvm/root"
password_file = "/etc/resticlvm/restic-password.txt"
prune_keep_last = 60
prune_keep_daily = 60
prune_keep_weekly = 24
prune_keep_monthly = 36
prune_keep_yearly = 10
```

### Example: Local + Copy to B2 (Recommended)

```toml
[[logical_volume_root.root.repositories]]
repo_path = "/backups/root-local"
password_file = "/etc/resticlvm/restic-password.txt"
prune_keep_last = 7
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 3
prune_keep_yearly = 1

  [[logical_volume_root.root.repositories.copy_to]]
  repo = "s3:s3.us-west-004.backblazeb2.com/mycompany-backups/resticlvm/root"
  password_file = "/etc/resticlvm/restic-password.txt"
  prune_keep_last = 60
  prune_keep_daily = 60
  prune_keep_weekly = 24
  prune_keep_monthly = 36
  prune_keep_yearly = 10
```

---

## Step 8: Automation

`rlvm-backup` loads B2 credentials from `/root/.config/resticlvm/b2-env` itself when
a config contains an `s3:` repo, so automation needs **no wrapper script** — just
run `rlvm-backup` as root.

### Cron

```cron
# Crontab entry (sudo crontab -e). Absolute path so cron's minimal PATH is irrelevant.
0 2 * * * /usr/local/bin/rlvm-backup --config /etc/resticlvm/backup.toml
```

### Systemd

```ini
# /etc/systemd/system/resticlvm-backup.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/rlvm-backup --config /etc/resticlvm/backup.toml
```

Credentials already present in the environment take precedence over the b2-env file,
so if you prefer to supply them inline instead of via the file you can add:

```ini
Environment="AWS_ACCESS_KEY_ID=your-key-id"
Environment="AWS_SECRET_ACCESS_KEY=your-app-key"
```

---

## Cost Estimation

### Storage Costs

- **Price**: $0.005/GB/month
- **Example**: 100 GB of backups = $0.50/month

### Transaction Costs

- **Class A** (uploads): $0.004 per 10,000 transactions
- **Class B** (downloads): $0.004 per 10,000 transactions
- **Typical cost**: < $0.10/month for daily backups

### Bandwidth Costs

- **Upload**: Free (unlimited)
- **Download**: $0.01/GB (first 1GB/day free)
- **Restores**: Usually within free tier

### Total Monthly Cost Example

Backing up 100 GB with daily snapshots:
- Storage: $0.50
- Transactions: $0.05
- Bandwidth: $0.00 (backups only)
- **Total: ~$0.55/month**

Compare to:
- AWS S3: ~$2.30/month (same data)
- Wasabi: $6.00/month (1TB minimum)

---

## Regions and Endpoints

Backblaze has multiple regions. Choose the closest to minimize latency:

| Region | Endpoint | Location |
|--------|----------|----------|
| us-west-004 | s3.us-west-004.backblazeb2.com | Western US |
| us-west-001 | s3.us-west-001.backblazeb2.com | Western US |
| us-east-005 | s3.us-east-005.backblazeb2.com | Eastern US |
| eu-central-003 | s3.eu-central-003.backblazeb2.com | Amsterdam |

Check your bucket details in B2 console for the exact region.

---

## Troubleshooting

### "Permission denied" or "Access denied"

**Cause**: Incorrect credentials or key permissions

**Solution**:
1. Verify you created an **S3-compatible** key (not regular B2 key)
2. Check key has **Read and Write** permissions
3. Verify key has access to your specific bucket
4. Check environment variables are exported: `echo $AWS_ACCESS_KEY_ID`

### "Connection timeout" or "Network error"

**Cause**: Network connectivity or firewall issues

**Solution**:
1. Test basic connectivity: `ping s3.us-west-004.backblazeb2.com`
2. Check firewall allows outbound HTTPS (port 443)
3. Try different region/endpoint
4. Check for proxy settings

### "Repository not found"

**Cause**: Incorrect bucket name or path

**Solution**:
1. Verify bucket exists in B2 console
2. Check bucket name spelling (case-sensitive)
3. Verify region matches bucket location
4. Try listing bucket contents in B2 web UI

### Environment variables not found

**Cause**: Variables not exported in current shell

**Solution**:
```bash
# Check if variables are set
echo $AWS_ACCESS_KEY_ID

# Source credential file
source /root/.config/resticlvm/b2-env

# For systemd, add to service file
Environment="AWS_ACCESS_KEY_ID=..."
```

### Storage not freed after pruning

**Cause**: Lifecycle rule not configured

**Solution**:
1. Verify lifecycle rule in bucket settings
2. Ensure rule is "Keep only the last version"
3. Wait 24 hours for B2 to delete old versions
4. Check bucket size in B2 console

---

## Security Best Practices

### Application Key Permissions

1. **Bucket-specific keys**: scope the key to a single bucket (not "All"), so a
   leaked key can't reach the rest of your account.
2. **Least privilege**: grant only what's needed. Note `restic prune`/`forget`
   require **delete** on the bucket — so a key used for pruning needs it. For
   stronger ransomware resistance, give the backup host a key **without** delete
   and run prune separately with a delete-capable key, and/or enable B2 **Object
   Lock** so existing snapshots can't be altered/removed.
3. **Key rotation**: Rotate keys periodically (every 90 days recommended)
4. **Expiration**: Consider setting key expiration dates

### Credential Storage

1. **File permissions**: Ensure credential files are `chmod 600` (root only)
2. **No version control**: Never commit credentials to git
3. **Encryption**: Consider encrypting credential files at rest
4. **Separate passwords**: Use different passwords for local and remote repos

### Restic Password Security

1. **Strong password**: Use 20+ character random password
2. **Password file**: Store in `/etc/resticlvm/restic-password.txt` (chmod 600)
3. **Backup password**: Store password in secure location (password manager)
4. **No recovery**: Lost password = lost data (no backdoor!)

---

## Monitoring and Maintenance

### Check Backup Status

```bash
# List snapshots
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  restic -r s3:s3.REGION.backblazeb2.com/BUCKET/PREFIX \
  --password-file /etc/resticlvm/restic-password.txt \
  snapshots'
```

### Verify Backup Integrity

```bash
# Check repository consistency
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  restic -r s3:s3.REGION.backblazeb2.com/BUCKET/PREFIX \
  --password-file /etc/resticlvm/restic-password.txt \
  check'
```

### Monitor B2 Usage

1. Log into B2 console
2. Navigate to **Billing** → **Usage**
3. Check:
   - Storage used (GB)
   - Transaction counts (Class A/B)
   - Download bandwidth
   - Monthly costs

### Cleanup Test Repositories

```bash
# Delete all snapshots and data (DANGEROUS!)
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  restic -r s3:s3.REGION.backblazeb2.com/BUCKET/PREFIX \
  --password-file /etc/resticlvm/restic-password.txt \
  forget --prune --keep-last 0'
```

---

## Additional Resources

- **B2 Documentation**: https://www.backblaze.com/docs/cloud-storage
- **Restic B2 Guide**: https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html
- **B2 Pricing Calculator**: https://www.backblaze.com/cloud-storage/pricing
- **B2 Status Page**: https://status.backblaze.com/

---

## Summary Checklist

Before running first backup, verify:

- [ ] B2 account created
- [ ] Bucket created with unique name
- [ ] Lifecycle rule set to "Keep only the last version"
- [ ] S3-compatible application key created (checkbox checked!)
- [ ] Credentials saved and stored securely
- [ ] Environment variables file created (`/root/.config/resticlvm/b2-env`)
- [ ] Repository initialized manually with restic
- [ ] ResticLVM config file created
- [ ] Test backup runs successfully
- [ ] Snapshots visible in restic and B2 web UI
- [ ] Monitoring/alerting configured (optional)

Once all checked, you're ready for production backups! 🎉
