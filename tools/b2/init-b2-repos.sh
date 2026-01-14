#!/bin/bash
# Initialize multiple B2 restic repositories
#
# This script initializes one or more restic repositories on Backblaze B2
# using the S3-compatible API. Requires B2 credentials to be sourced.

set -e

# Usage information
usage() {
  cat << EOF
Usage: $(basename "$0") [OPTIONS] REPO_NAME [REPO_NAME...]

Initialize one or more restic repositories on Backblaze B2.

Required Arguments:
  REPO_NAME             One or more repository names (paths within bucket)

Options:
  -b, --bucket BUCKET   B2 bucket name (required)
  -r, --region REGION   B2 region (required, e.g., us-west-004)
  -p, --prefix PREFIX   Path prefix within bucket (optional)
  -P, --password FILE   Restic password file (required)
  -h, --help            Show this help message

Environment:
  Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to be set
  (typically sourced from a credentials file)

Examples:
  # Initialize single repository
  $(basename "$0") -b my-bucket -r us-west-004 -P /path/to/password.txt my-repo

  # Initialize with prefix
  $(basename "$0") -b my-bucket -r us-west-004 -p my-host -P /path/to/password.txt repo1 repo2

  # Initialize multiple repositories
  $(basename "$0") -b my-bucket -r us-west-004 -P /path/to/password.txt \\
    root-direct root-copied data-direct data-copied

  # With sourced credentials
  source /root/.config/restic/b2-env
  $(basename "$0") -b resticlvm-test -r us-west-004 -P /root/.restic-password \\
    backup/root backup/data

EOF
  exit 1
}

# Default values
BUCKET=""
REGION=""
PREFIX=""
PASSWORD_FILE=""
REPOS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--bucket)
      BUCKET="$2"
      shift 2
      ;;
    -r|--region)
      REGION="$2"
      shift 2
      ;;
    -p|--prefix)
      PREFIX="$2"
      shift 2
      ;;
    -P|--password)
      PASSWORD_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo "Error: Unknown option: $1"
      echo ""
      usage
      ;;
    *)
      # Positional argument - repository name
      REPOS+=("$1")
      shift
      ;;
  esac
done

# Validate required arguments
if [ -z "$BUCKET" ]; then
  echo "Error: Bucket name is required (-b/--bucket)"
  echo ""
  usage
fi

if [ -z "$REGION" ]; then
  echo "Error: Region is required (-r/--region)"
  echo ""
  usage
fi

if [ -z "$PASSWORD_FILE" ]; then
  echo "Error: Password file is required (-P/--password)"
  echo ""
  usage
fi

if [ ${#REPOS[@]} -eq 0 ]; then
  echo "Error: At least one repository name is required"
  echo ""
  usage
fi

# Validate password file exists
if [ ! -f "$PASSWORD_FILE" ]; then
  echo "Error: Password file not found: $PASSWORD_FILE"
  exit 1
fi

# Validate credentials are set
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  echo "Error: B2 credentials not found in environment"
  echo "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
  echo "Example: source /root/.config/restic/b2-env"
  exit 1
fi

# Build base URL
BASE_URL="s3:s3.$REGION.backblazeb2.com/$BUCKET"
if [ -n "$PREFIX" ]; then
  BASE_URL="$BASE_URL/$PREFIX"
fi

# Display summary
echo "Initializing B2 restic repositories"
echo "========================================================"
echo "Bucket:        $BUCKET"
echo "Region:        $REGION"
if [ -n "$PREFIX" ]; then
  echo "Prefix:        $PREFIX"
fi
echo "Password File: $PASSWORD_FILE"
echo "Repositories:  ${#REPOS[@]}"
echo "========================================================"
echo ""

# Initialize repositories
SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_REPOS=()

for REPO in "${REPOS[@]}"; do
  REPO_URL="$BASE_URL/$REPO"
  echo "Initializing: $REPO_URL"
  
  if restic -r "$REPO_URL" init --password-file "$PASSWORD_FILE"; then
    echo "✅ Success: $REPO"
    ((SUCCESS_COUNT++))
  else
    echo "❌ Failed: $REPO"
    ((FAILED_COUNT++))
    FAILED_REPOS+=("$REPO")
  fi
  echo ""
done

# Summary
echo "========================================================"
echo "Initialization Complete"
echo "========================================================"
echo "Success: $SUCCESS_COUNT"
echo "Failed:  $FAILED_COUNT"
echo ""

if [ $FAILED_COUNT -gt 0 ]; then
  echo "Failed repositories:"
  for REPO in "${FAILED_REPOS[@]}"; do
    echo "  ❌ $REPO"
  done
  echo ""
  exit 1
fi

echo "All repositories initialized successfully!"
echo ""
echo "Repository URLs:"
for REPO in "${REPOS[@]}"; do
  echo "  $BASE_URL/$REPO"
done
