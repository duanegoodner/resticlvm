# B2 Integration Testing Plan

## Overview

Backblaze B2 can be used with restic in two ways:
1. **Native B2 API** (`b2:bucket:prefix`) - NOT RECOMMENDED due to error handling issues
2. **S3-Compatible API** (`s3:s3.region.backblazeb2.com/bucket`) - **RECOMMENDED** by restic developers

Per restic documentation, the S3-compatible API has better error handling and is more reliable. We'll focus on testing the S3-compatible approach.

**Note**: Native B2 API exists and ResticLVM supports it, but we recommend using S3-compatible for production use.

---

## Phase 1: B2 Account Setup

### 1.1 Create Backblaze Account
- Sign up at https://www.backblaze.com/b2/sign-up.html
- Free tier: 10 GB storage, 1 GB/day download (sufficient for testing)
- No credit card required for free tier

### 1.2 Create B2 Bucket
- Navigate to "B2 Cloud Storage" → "Buckets" → "Create a Bucket"
- **Bucket Name**: `resticlvm-test-<random>` (must be globally unique)
- **Files in Bucket**: Private
- **Lifecycle Settings**: Keep only the last version of the file
- **Note the bucket region** - will be needed for S3-compatible API (e.g., `us-west-004`)

### 1.3 Configure Lifecycle Rule (MANDATORY)
4 Create S3-Compatible Application Key

- Go to "App Keys" → "Add a New Application Key"
- **Name**: `resticlvm-s3-test`
- **IMPORTANT: Check "S3 Compatible" box!** (generates different credentials)
- **Allow access to**: Specific bucket (select your test bucket)
- **Type of Access**: Read and Write
- **File name prefix**: Leave empty (or use a prefix like `resticlvm/`)
- **Duration**: No limit (or set expiration for security)
- **Save credentials immediately** - you only see them once!
  - `keyID` → This is your **AWS_ACCESS_KEY_ID**
  - `applicationKey` → This is your **AWS_SECRET_ACCESS_KEY**)
- **File name prefix**: Leave empty (or use a prefix like `resticlvm-root/`)
- **Duration**: No limit (or set expiration for security)
- **Save credentials immediately** - you only see them once!
  - `keyID` → This is your B2_ACCOUNT_ID
  - `applicationKey` → This is your B2_ACCOUNT_KEY

**For S3-Compatible API:**
- Go to "App Keys" → "Add a New Application Key"
- **Name**: `resticlvm-s3-test`
- **S3 Compatible**: Check this box!
- **Allow access to**: Same bucket
- **Type of Access**: Read and Write
- **Save credentials:**
  - `keyID` → This is your AWS_ACCESS_KEY_ID
  - `applicationKey` → This is your AWS_SECRET_ACCESS_KEY

---

## Phase 2: Local Testing Preparation

### 2.1 Store Credentials Securely

**For Native B2:**
```bash
# Create secure credential file (root only)
sudo mkdir -p /root/.config/restic
sudo chmod 700 /root/.config/restic

# Store B2 credentials
sudo tee /root/.config/restic/b2-env << 'EOF'
export B2_ACCOUNT_ID="your-key-id-here"
export B2_ACCOUNT_KEY="your-application-key-here"
EOF
```bash
# Create secure credential file (root only)
sudo mkdir -p /root/.config/restic
sudo chmod 700 /root/.config/restic

# Store S3-compatible B2 credentials
sudo tee /root/.config/restic/b2-env << 'EOF'
export AWS_ACCESS_KEY_ID="your-key-id-here"
export AWS_SECRET_ACCESS_KEY="your-application-key-here"
EOF

sudo chmod 600 /root/.config/restic/b2

## Phase 3: Manual Testing (Before ResticLVM)

### 3.1 Test Native B2 with Plain Restic

```bash
# Source credentials
source /root/.config/restic/b2-env

# Initialize repository
restic -r b2:resticlvm-test-<random>:root-test \
  init --password-file /home/debian/test-passwords/restic.txt

# Test backup
restic -r b2:resticlvm-test-<random>:root-test \
  --password-file /home/debian/test-passwords/restic.txt \
  backup /etc
S3-compatible backup (standard path)
2. Direct B2 S3-compatible backup (LV)
3 --password-file /home/debian/test-passwords/restic.txt \
  snapshots

# Test restore (to /tmp)
restic -r b2:resticlvm-test-<random>:root-test \
  --password-file /home/debian/test-passwords/restic.txt \
  restore latest --target /tmp/restore-test
S3-Compatible B2 and show uploaded data
- ✅ Snapshots should list the backup
- ✅ Restore should work

---

## Phase 4: ResticLVM Integration Testing

### 4.1 Create Test Config - Direct B2 Native

```toml
# test/test-configs-private/backup-test-b2-native.toml

[standard_path.test-b2-native]
backup_source_path = "/etc"
exclude_paths = []
remount_readonly = false

[[standard_path.test-b2-native.repositories]]
repo_path = "b2:resticlvm-test-<random>:resticlvm/root-native"
password_file = "/home/debian/test-passwords/restic.txt"
prune_keep_last = 5
prune_keep_daily = 3env

# Initialize repository
# Replace us-west-004 with your bucket's region
# Replace resticlvm-test-<random> with your actual bucket name
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/manual-test \
  init --password-file /home/debian/test-passwords/restic.txt

# Test backup
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/manual-test \
  --password-file /home/debian/test-passwords/restic.txt \
  backup /etc

# List snapshots
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/manual-test \
  --password-file /home/debian/test-passwords/restic.txt \
  snapshots

# Test restore (to /tmp)
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/manual-test \
  --password-file /home/debian/test-passwords/restic.txt \
  restore latest --target /tmp/restore-test

# Verify restore
ls -la /tmp/restore-test/etc

# Cleanup
rm -rf /tmp/restore-test
[[standard_path.test-b2-s3.repositories(Standard Path)
repo_path = "/srv/backup/test-b2-local"
password_file = "/home/debian/test-passwords/restic.txt"
prune_keep_last = 3
prune_keep_daily = 2
prune_keep_weekly = 1
prune_keep_monthly = 1
prune_keep_yearly = 1

  # Copy to B2 native
  [[standard_path.test-b2-copy.repositories.copy_to]]
  repo = "b2:resticlvm-test-<random>:resticlvm/root-copied"
  password_file = "/home/debian/test-passwords/restic.txt"
  prune_keep_last = 10
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 6
  prune_keep_yearly = 2
```

### 4.4 Run Tests

**Test 1: Direct B2 Native**
```bashdirect.toml

[standard_path.test-b2-direct]
backup_source_path = "/etc"
exclude_paths = []
remount_readonly = false

[[standard_path.test-b2-direct.repositories]]
repo_path = "s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/etc-direct"
password_file = "/home/debian/test-passwords/restic.txt"
prune_keep_last = 5
prune_keep_daily = 3
prune_keep_weekly = 2
prune_keep_monthly = 1
prune_keep_yearly = 1
```

### 4.2 Create Test Config - Direct B2 (LV Backup)

```toml
# test/test-configs-private/backup-test-b2-lv.toml

[lv_backup.test-b2-lv]
backup_source_lv = "/dev/vg0/data-lv"
backup_source_mS3-compatible
  [[standard_path.test-b2-copy.repositories.copy_to]]
  repo = "s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/etc
exclude_paths = []

[[lv_backup.test-b2-lv.repositories]]
repo_path = "s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/data-lv-direct
rlvm-backup --config test/test-configs-private/backup-test-b2-native.toml

# Verify in B2 web UI
# Check: Browse Files → resticlvm/root-native/ should have restic data
```

**Test 2: Direct B2 (Standard Path)**
```bash
# Source B2 credentials
source /root/.config/restic/b2-env

# Initialize repo manually first
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/etc-direct \
  init --password-file /home/debian/test-passwords/restic.txt

# Run ResticLVM backup
rlvm-backup --config test/test-configs-private/backup-test-b2-direct.toml

# Verify in B2 web UI
# Check: Browse Files → resticlvm/etc-direct/ should have restic data

# Verify snapshots
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/etc-direct \
  --password-file /home/debian/test-passwords/restic.txt \
  snapshots
```

**Test 2: Direct B2 (LV Backup)**
```bash
# Source credentials
source /root/.config/restic/b2-env

# Initialize repo
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/data-lv-direct \
  init --password-file /home/debian/test-passwords/restic.txt

# Run ResticLVM backup
rlvm-backup --config test/test-configs-private/backup-test-b2-lv.toml

# Verify
restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/data-lv-direct \
  --password-file /home/debian/test-passwords/restic.txt \
  snapshots
```

**Test 3: Local with Copy to B2**
```bash
# Source B2 credentials
source /root/.config/restic/b2-env

# Initialize local and B2 repos
mkdir -p /srv/backup/test-b2-local
restic -r /srv/backup/test-b2-local \
  init --password-file /home/debian/test-passwords/restic.txt

restic -r s3:s3.us-west-004.backblazeb2.com/resticlvm-test-<random>/resticlvm/etc-copied \
  init --password-file /home/debian/test-passwords/restic.txt

# Run ResticLVM backup (S3-Compatible API - RECOMMENDED)

**Per restic documentation, use S3-compatible API for better error handling:**

1. Create B2 bucket with "Keep only the last version of the file" lifecycle rule
2. Create **S3-compatible** application key (check "S3 Compatible" box in B2 UI)
3. Export credentials:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key-id"
   export AWS_SECRET_ACCESS_KEY="your-app-key"
   ```
4. Use repo format: `s3:s3.region.backblazeb2.com/bucket/prefix`
5. Find your region in B2 UI (e.g., `us-west-004`, `eu-central-003`)

**Note**: Native B2 API (`b2:bucket:prefix`) is supported but not recommended due to error handling issues in the underlying library.
### 6.1 Update README.md

Add B2 setup section:

```markdown
#### Backblaze B2 Setup

**Native B2 API** (recommended):
1. Create B2 bucket and application key
2. Export credentials:
   ```bash
   export B2_ACCOUNT_ID="your-account-id"
   export B2_ACCOUNT_KEY="your-app-key"
   ```
3. Use repo format: `b2:bucket-name:prefix`

**S3-Compatible API**:
1. Create B2 bucket and S3-compatible application key
2. Export credentials:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key-id"
   export AWS_SECRET_ACCESS_KEY="your-app-key"
   ```
3. Use repo format: `s3:s3.region.backblazeb2.com/bucket/prefix`
```

### 6.2 Update Example Configs

Update `docs/test-config-examples/direct-b2-backup.toml` with tested values.

### 6.3 Add B2 Notes to EXAMPLE_SSH_SETUP.md

Or create `EXAMPLE_B2_SETUP.md` with:
- Account creation steps
- Application key creation (both types)
- Cost considerations (free tier limits)
- Lifecycle rules setup (optional)
- Security best practices

---

## Phase 7: Known Considerations

### Environment Variable Handling

ResticLVM already passes environment through `subprocess.run(env=env)`, so B2 credentials should work. But verify:

1. **For cron jobs**: Ensure cron wrapper exports B2 credentials
2. **For systemd**: Add B2 credentials to service file
3. **For manual runs**: Source credential file before running

### Cost Optimization

B2 charges for:
- **Storage**: $0.005/GB/month (free tier: 10GB)
- **Download**: $0.01/GB (free tier: 1GB/day)
- **Transactions**: Class A (uploads) $0.004/10k, Class B (downloads) $0.004/10k

**Recommendations:**
- Use aggressive pruning for B2 to minimize storage
- Use `copy_to` approach (backup local first) to minimize failed uploads
- Consider B2 lifecycle rules for auto-deletion

### Region Selection

B2 has multiple regions:
- `us-west-004` (US West)
- `us-west-001` (US West)
- `eu-central-003` (EU Central)

Choose closest to minimize latency.

---

## Phase 8: Success Criteria

✅ **Must have:**
- Direct B2 native backup works
- Direct B2 S3-compatible backup works
- Local with copy_to B2 works
- All snapshots restorable
- Pruning works correctly
- Documentatbackup works (standard path)
- Direct B2 backup works (LV)
- Local with copy_to B2 works
- All snapshots restorable
- Pruning works correctly
- Lifecycle rule deletes old versions (verify in B2 UI after 1+ days)al use
- Lifecycle rule examples
- Multi-region setup example

---

## Implementation Order

1. ✅ Create B2 account and bucket
2. ✅ Create application keys (native + S3)
3. ✅ Manual restic testing (verify credentials work)
4. ✅ Create ResticLVM test configs
5. ✅ Test direct B2 native
6. ✅ Tonfigure lifecycle rule (keep only last version)
3. ✅ Create S3-compatible application key
4. ✅ Store credentials securely
5. ✅ Manual restic testing (verify credentials work)
6. ✅ Create ResticLVM test configs
7. ✅ Test direct B2 (standard path)
8. ✅ Test direct B2 (LV backup)
9. ✅ Test local + copy_to B2
10. ✅ Validate all features
11. ✅ Update documentation
12 Troubleshooting Guide

**"Permission denied" or "Access denied":**
- Check application key has correct permissions
- Verify "Allow List All Bucket Names" is enabled
- Check bucket name spelling

**"Connection timeout" or "Network error":**
- Check internet connectivity
- Verify you created an **S3-Compatible** application key (not regular B2 key)
- Check application key has correct permissions
- Check bucket name spelling
- Ensure credentials are exported: `echo $AWS_ACCESS_KEY_ID`
**"Repository not found":**
- Ensure bucket exists
- Check prefix/path formatting
- Verify credentials are for correct account

**Environment variables not found:**
- Check variables are exported: `echo $B2_ACCOUNT_ID`
- Source credential file in current shell
- For systemd: Add to Environment= directive

---AWS_ACCESS_KEY_ID`
- Source credential file in current shell: `source /root/.config/restic/b2-env`
## Next Steps After B2 Testing

1. Create PR for B2 integration (if any code changes needed)
2. Test Azure/GCS if desired
3. Performance comparison (local vs SFTP vs B2)
4. Create new release (v0.2.0?)
5. Update changelog with all features since last release
