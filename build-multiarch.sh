#!/bin/bash
# Multi-architecture Docker build script for SSH MCP Bridge
# Builds for both linux/amd64 and linux/arm64 (macOS)

set -e

# Configuration
IMAGE_NAME="ssh-mcp-bridge"
VERSION="${1:-2.0.0}"
REGISTRY="shashikanthg"
TAG="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

echo "=== SSH MCP Bridge Multi-Architecture Build ==="
echo "Image: ${TAG}"
echo "Platforms: linux/amd64, linux/arm64"
echo ""

# Check if buildx is available
if ! docker buildx version &> /dev/null; then
    echo "Error: docker buildx is not available"
    echo "Please install Docker Desktop or enable buildx"
    exit 1
fi

# Create builder instance if it doesn't exist
BUILDER_NAME="ssh-mcp-multiarch"
if ! docker buildx inspect ${BUILDER_NAME} &> /dev/null; then
    echo "Creating buildx builder instance: ${BUILDER_NAME}"
    docker buildx create --name ${BUILDER_NAME} --driver docker-container --use
    docker buildx inspect --bootstrap
else
    echo "Using existing buildx builder: ${BUILDER_NAME}"
    docker buildx use ${BUILDER_NAME}
fi

echo ""
echo "Building multi-architecture image..."
echo ""

# Build for multiple architectures (does NOT push)
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t ${TAG} \
    -f Dockerfile \
    . 2>&1 || {
        echo ""
        echo "Note: Multi-platform builds cannot use --load (local docker)"
        echo "Image is built but stored in buildx cache only"
        echo ""
        echo "To test locally, build for your platform only:"
        echo "  docker build -t ${TAG} ."
        echo ""
        exit 1
    }

echo ""
echo "✓ Multi-architecture image built successfully!"
echo ""
echo "Built: ${TAG}"
echo "Platforms: linux/amd64, linux/arm64"
echo ""
echo "NOTE: Image is built but NOT pushed to registry"
echo ""
echo "To push manually:"
echo "  docker buildx build --platform linux/amd64,linux/arm64 -t ${TAG} --push ."
echo ""
echo "To also tag as latest:"
echo "  docker buildx build --platform linux/amd64,linux/arm64 -t ${TAG} -t ${REGISTRY}/${IMAGE_NAME}:latest --push ."
echo ""
