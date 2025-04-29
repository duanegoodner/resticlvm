.PHONY: build clean install check-version release distclean

# Build source and wheel distributions
build:
	@echo "📦 Building dist/ artifacts..."
	python -m build

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build dist *.egg-info

# Clean everything and rebuild
distclean: clean build

# Reinstall from latest built wheel
install:
	@echo "⬇️ Installing latest wheel..."
	pip install --force-reinstall dist/*.whl

# Check if built wheel has correct Python version requirement
check-version:
	@echo "🔍 Checking 'Requires-Python' in built wheel..."
	unzip -p dist/*.whl *.dist-info/METADATA | grep Requires-Python || echo "❌ Not found"

# Build + check version + print reminder to tag
release: clean build check-version
	@echo ""
	@echo "✅ Build complete. To release:"
	@echo "   git tag vX.Y.Z && git push origin vX.Y.Z"
	@echo "   Then draft a GitHub release and attach dist/*.whl"

