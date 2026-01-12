#!/bin/bash

# Build and release automation for Python package distribution
#
# Usage:
#   ./tools/build-release.sh
#
# Requirements:
#   - python -m build (install with: pip install build)
#   - unzip command available in PATH

set -e

echo "🧹 Cleaning build artifacts..."
rm -rf build dist *.egg-info

echo ""
echo "📦 Building distribution packages..."
python -m build

echo ""
echo "🔍 Checking 'Requires-Python' in built wheel..."
unzip -p dist/*.whl *.dist-info/METADATA | grep Requires-Python || echo "❌ Not found"

echo ""
echo "✅ Build complete!"
echo ""
echo "📝 Next steps to release:"
echo "   1. git tag vX.Y.Z"
echo "   2. git push origin vX.Y.Z"
echo "   3. Create a GitHub release and attach dist/*.whl"
