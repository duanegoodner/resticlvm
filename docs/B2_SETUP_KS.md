# B2 Setup — Kernel State

Live setup log for configuring Backblaze B2 following the
[Kernel State B2 guidelines](https://github.com/duanegoodner/workstation-ops/blob/main/cloud-storage/b2-management.md).
Each section is added after the step has been successfully executed on fraser.

For the previous generic setup guide, see [EXAMPLE_B2_SETUP.md](EXAMPLE_B2_SETUP.md).

## Prerequisites

- [x] `pipx` and `b2` CLI installed on fraser (`pipx install b2`, v4.7.1)
- [x] Master key regenerated and saved to Bitwarden (transient use only)

## 1. Bucket lifecycle — 90-day version retention

Updated `kernelstate-backups` lifecycle from "delete after 1 day" to 90-day retention
for non-current versions (ransomware defense window per org guidelines).

```bash
b2 bucket update --lifecycle-rule \
  '{"daysFromHidingToDeleting": 90, "fileNamePrefix": ""}' \
  kernelstate-backups
```

Verified: `"daysFromHidingToDeleting": 90` in `b2 bucket get` output.

## 2. Application key — `resticlvm-fraser`

Created via B2 CLI with minimal capabilities, scoped to fraser's prefix:

```bash
b2 key create \
  --bucket kernelstate-backups \
  --name-prefix 'resticlvm/fraser/' \
  resticlvm-fraser \
  listBuckets,listFiles,readFiles,writeFiles,deleteFiles
```

Key ID and secret saved to Bitwarden immediately.

## 3. On-host credential storage

Stored at `/root/.config/resticlvm/b2-env` (mode 0600, root:root). Contains
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` for the scoped fraser key.
`rlvm backup` loads this file automatically when a config contains an `s3:` repo.

## 4. Initialize B2 repos

Used `tools/b2/init-b2-repos.sh` to create 6 repos under
`kernelstate-backups/resticlvm/fraser/`:

```bash
sudo bash -c 'source /root/.config/resticlvm/b2-env && \
  tools/b2/init-b2-repos.sh \
    -b kernelstate-backups -r us-west-004 \
    -p resticlvm/fraser \
    -P /root/.config/resticlvm/repo-creds/fraser-b2 \
    efi-01 boot-01 root-01 git-01 mail-01 core-01'
```

**Note:** `init-b2-repos.sh` had a bug where `((SUCCESS_COUNT++))` exited under
`set -e` when incrementing from 0. Fixed with `|| true`.

## 5. Fraser backup config

B2 repos were already present in `fraser-backup.toml` (added when the config was
originally created). Each volume has three repository entries: local, anchor (SFTP),
and B2 — all using the `standard` prune policy.

## 6. Test backup run (2026-07-10)

Initial seed to B2 — all 6 volumes succeeded:

| Volume | Files | Size | Stored | Snapshot |
|--------|------:|-----:|-------:|----------|
| efi | 12 | 49 MiB | 21 MiB | `767e37c6` |
| boot | 357 | 552 MiB | 481 MiB | `7f5168c3` |
| root | 561,703 | 42 GiB | 18.6 GiB | `b7c8b57a` |
| git | 6,951 | 4.3 GiB | 1.0 GiB | `69f9b32f` |
| mail | 2,556 | 1.2 GiB | 481 MiB | `69003ef5` |
| core | 75 | 81 MiB | 75 MiB | `0822cbd6` |

Total stored: ~20.6 GiB. Local and anchor repos failed as expected (not yet
initialized on the post-migration layout).

## Still TODO

- [ ] Set billing alert ($10/month) in B2 account settings
- [ ] Initialize local repos under `/backup/resticlvm/`
- [ ] Fix anchor SFTP access (SSH agent / key)
