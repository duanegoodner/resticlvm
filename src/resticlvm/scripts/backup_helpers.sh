#!/bin/bash

# Aggregates and sources all helper libraries needed for backup scripts.
#
# This file allows main backup scripts to load all necessary functionality
# (argument parsing, snapshot handling, mount management, etc.) from a single
# point without sourcing each helper individually.
#
# Usage:
#   Intended to be sourced by other scripts within the ResticLVM tool.
#
# Requirements:
#   - Must be sourced from scripts located in the same directory structure.
#   - Helper scripts must remain compatible with being sourced together.
#
# Exit codes:
#   N/A (this script is only meant to be sourced, not executed directly)

# shellcheck disable=SC1091

source "$(dirname "$0")/lib/arg_handlers.sh"
source "$(dirname "$0")/lib/command_builders.sh"
source "$(dirname "$0")/lib/command_runners.sh"
source "$(dirname "$0")/lib/lv_snapshots.sh"
source "$(dirname "$0")/lib/message_display.sh"
source "$(dirname "$0")/lib/mounts.sh"
source "$(dirname "$0")/lib/pre_checks.sh"
source "$(dirname "$0")/lib/usage_commands.sh"
