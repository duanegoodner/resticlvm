# ResticLVM Tools

This directory contains utility scripts for development, testing, and deployment.

## Available Tools

### build-release.sh
Build and package ResticLVM for distribution.

**Usage:**
```bash
./tools/build-release.sh
```

**Requirements:**
- python -m build (install with: `pip install build`)

---

### init-b2-repos.sh
Initialize multiple restic repositories on Backblaze B2.

**Usage:**
```bash
./tools/init-b2-repos.sh [OPTIONS] REPO_NAME [REPO_NAME...]
```

**Options:**
- `-b, --bucket BUCKET` - B2 bucket name (required)
- `-r, --region REGION` - B2 region (required, e.g., us-west-004)
- `-p, --prefix PREFIX` - Path prefix within bucket (optional)
- `-P, --password FILE` - Restic password file (required)
- `-h, --help` - Show help message

**Requirements:**
- B2 credentials in environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- restic installed and available in PATH

**Example:**
```bash
# Source credentials
source /root/.config/restic/b2-env

# Initialize repositories for a host
./tools/init-b2-repos.sh \
  -b resticlvm-test-0001 \
  -r us-west-004 \
  -p debian13-vm \
  -P /home/debian/test-passwords/restic.txt \
  root-direct root-copied data-lv-direct data-lv-copied
```
