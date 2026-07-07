# fraser VM toolchain — ready for use

> **Date:** 2026-07-06

fraser's KVM/Packer/libvirt toolchain is installed and verified. The setup was done in the
workstation-ops repo; the permanent record lives at
`workstation-ops/workstations/fraser/vm-dev-tooling.md`.

## What's ready

- **Storage split:** Packer build output (temporary, ~30 GB) stays in the project tree under
  `/data/git` — standard `output-<builder>/` convention, `.gitignore`d. Deployed VM disks go to
  the default libvirt pool at `/var/lib/libvirt/images` (on root VG, ~850 GB free). Build output
  can be cleaned up after a successful deploy.
- `/data/git` LV extended to 60 GB (was 20 GB) — room for project source + one active build.
- Packer 1.15.4, QEMU 10.0.8, libvirt 11.3.0, virt-install 5.0.0, Ansible core 2.19.4.
- `libvirt,kvm` groups active; `libvirtd` enabled; default network active + autostart.
- SSH key: `~/.ssh/vm-dev` / `~/.ssh/vm-dev.pub` (ed25519, `vm-dev@fraser`).

## VM status (updated 2026-07-06)

The `debian13-vm` VM is **deployed and running** on fraser. Steps 1-4 below are complete.

### Build / deploy / reconnect

```bash
# Build (~10-20 min, only needed if image changes)
cd dev/vm-builder/packer-local
packer init .          # first time only
./scripts/build.sh

# Deploy
cd dev/vm-builder/deploy-local
sudo ./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --ssh-key ~/.ssh/vm-dev.pub

# Wait ~1-2 min for LVM migration + reboot, then:
sudo virsh domifaddr debian13-vm
ssh -i ~/.ssh/vm-dev debian@<IP>
```

### Tear down / redeploy

```bash
sudo virsh destroy debian13-vm
sudo virsh undefine debian13-vm --remove-all-storage --nvram
# Then re-run deploy above
```

### Build steps completed

1. **Config:** pixi on (default), miniconda off (default), restic on (default) — no env var
   overrides needed. Implemented upstream in `duanegoodner/vm-builder` PR #4, re-cloned
   into `dev/vm-builder/` at commit 92656f9.
2. **Build:** `cd dev/vm-builder/packer-local && packer init . && ./scripts/build.sh`
3. **Deploy:** `cd dev/vm-builder/deploy-local && sudo ./deploy.sh ... --ssh-key ~/.ssh/vm-dev.pub`
4. **SSH in:** `ssh -i ~/.ssh/vm-dev debian@<IP>` (get IP via `sudo virsh domifaddr debian13-vm`)

See `dev/vm-builder/README.md` for full build/deploy docs.

## Python env in the VM (decided 2026-07-06): pixi in, miniconda out

Use **pixi** for Python/project env management in the VM — it matches resticlvm's bare-metal dev
workflow (clone + `pixi install` editable, edit `scripts/lib/*.sh`, test with
`sudo "$(command -v rlvm)" backup`). **Drop miniconda:** its bare-metal value (an always-on
non-system-python default shell) is redundant in a disposable VM where system Python is PEP-668
externally-managed and pixi owns the project env, and it reintroduces the conda-shadows-`python3`
quirk.

Implemented in vm-builder PR #4: `INSTALL_PIXI` defaults to `true`, `INSTALL_MINICONDA` defaults
to `false`. Override with env vars if needed (e.g. `INSTALL_MINICONDA=true INSTALL_PIXI=false`).

## Gotchas to know

- Packer plugins (`qemu` + `ansible`) come from `packer init`, not apt.
- `sudo virsh net-list` (not unprivileged) to see networks.
- `cloud.debian.org` can be unreliable; Packer is configured with a fallback mirror
  (`gemmei.ftp.acc.umu.se`). Checksum also points at the fallback.
- `virsh undefine` requires `--nvram` flag (VM uses UEFI).
