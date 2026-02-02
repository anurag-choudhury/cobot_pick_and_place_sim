#!/usr/bin/env bash
set -e

IMAGE_NAME="manipulation"
IMAGE_TAG="latest"

echo "========================================"
echo " Building Docker Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "========================================"

docker build \
  -t ${IMAGE_NAME}:${IMAGE_TAG} \
  .

echo ""
echo "========================================"
echo " Build Completed Successfully"
echo " Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "========================================"
echo ""

echo "To run:"
echo "  ./run.sh"
