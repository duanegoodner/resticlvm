#!/bin/bash

# Optional tools configuration
# Controls installation of additional software in VM images
# Used by both local and AWS builds

# Set to 'true' to install, 'false' to skip
export INSTALL_MINICONDA=${INSTALL_MINICONDA:-false}
export INSTALL_PIXI=${INSTALL_PIXI:-true}
export INSTALL_RESTIC=${INSTALL_RESTIC:-true}

# Tool versions
export MINICONDA_VERSION="latest"
