# Release Tools

Tools for building and packaging ResticLVM releases.

## Files

- `build-release.sh` - Build script for creating release packages
- `environment.yml` - Conda environment specification for the build environment

## Usage

```bash
cd tools/release
./build-release.sh
```

The build script will create a conda environment (if needed) and build the ResticLVM package.
