#!/usr/bin/env bash
# download_bird.sh - Script to download and extract the BIRD benchmark dataset

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST_DIR="$PROJECT_ROOT/pamo_sql/data/raw/bird"
TYPE=${1:-"dev"}

if [ "$TYPE" = "train" ]; then
  URL="https://bird-bench.oss-cn-beijing.aliyuncs.com/train.zip"
  ZIP_NAME="train.zip"
  echo "Preparing to download BIRD Full Train Dataset (WARNING: approx. 30 GB+)..."
elif [ "$TYPE" = "dev" ]; then
  URL="https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
  ZIP_NAME="dev.zip"
  echo "Preparing to download BIRD Full Dev Dataset (approx. 4.5 GB)..."
else
  echo "Error: Invalid argument '$TYPE'. Choose 'train' or 'dev'."
  exit 1
fi

# Create target directory
mkdir -p "$DEST_DIR"

# Download ZIP file
echo "Downloading $ZIP_NAME from $URL ..."
if command -v wget &> /dev/null; then
  wget -O "$PROJECT_ROOT/$ZIP_NAME" "$URL"
elif command -v curl &> /dev/null; then
  curl -L -o "$PROJECT_ROOT/$ZIP_NAME" "$URL"
else
  echo "Error: Neither wget nor curl found. Please install one of them to download the dataset."
  exit 1
fi

# Unzip to target directory
echo "Extracting $ZIP_NAME to $DEST_DIR ..."
unzip -o "$PROJECT_ROOT/$ZIP_NAME" -d "$DEST_DIR"

# Clean up downloaded zip
rm "$PROJECT_ROOT/$ZIP_NAME"

echo "=== BIRD Dataset download and extraction completed successfully! ==="
echo "Dataset resides in: $DEST_DIR"
