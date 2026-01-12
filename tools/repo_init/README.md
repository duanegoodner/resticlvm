# Repository Initialization Tools

Scripts for initializing Restic repositories.

## Files

- `init-b2-repos.sh` - Initialize Backblaze B2 repositories for testing

## Usage

This script requires B2 credentials configured in the environment:

```bash
# Set B2 credentials
export B2_ACCOUNT_ID="your-account-id"
export B2_ACCOUNT_KEY="your-account-key"

# Run initialization
./init-b2-repos.sh
```

See the script header for detailed configuration requirements and what repositories will be created.
