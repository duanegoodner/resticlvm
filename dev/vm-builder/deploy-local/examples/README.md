# Deploy Local Examples

Example configurations for local VM deployment.

## Basic Deployment

```bash
cd /data/duane/git/vm-builder/deploy-local
./deploy.sh ../packer-local/output/debian13-local/debian13-local
```

## Custom Configuration

```bash
./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name dev-vm \
  --memory 8192 \
  --vcpus 4 \
  --lvm-disk-size 50G \
  --ssh-key ~/.ssh/id_rsa.pub
```

## Example Cloud-init Customization

See `user-data-example.yaml` for cloud-init customization options.

## Multiple VMs

```bash
# Development VM
./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name dev-vm --memory 8192 --vcpus 4

# Test VM
./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name test-vm --memory 4096 --vcpus 2

# Database VM  
./deploy.sh ../packer-local/output/debian13-local/debian13-local \
  --name db-vm --memory 16384 --vcpus 8 --lvm-disk-size 100G
```
