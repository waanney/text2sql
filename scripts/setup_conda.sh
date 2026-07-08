#!/usr/bin/env bash
# setup_conda.sh - Script to install Miniconda and set up the PAMO-SQL Python environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_NAME="pamo_sql"
PYTHON_VERSION="3.11"

# 1. Install Conda if not available
if ! command -v conda &> /dev/null; then
    echo "Conda not found. Downloading and installing Miniconda3..."
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    INSTALL_SCRIPT="/tmp/miniconda.sh"
    
    wget -qO "$INSTALL_SCRIPT" "$MINICONDA_URL"
    bash "$INSTALL_SCRIPT" -b -u -p "$HOME/miniconda3"
    rm "$INSTALL_SCRIPT"
    
    # Initialize conda in current shell
    eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
    echo "Miniconda installed successfully."
else
    echo "Conda is already installed."
    # Ensure conda hook is active
    eval "$(conda shell.bash hook)"
fi

# 2. Create the Conda environment
echo "Creating Conda environment: $ENV_NAME with Python $PYTHON_VERSION..."
# Remove existing environment if it exists (optional, keeping it safe by just checking)
if conda info --envs | grep -q "^$ENV_NAME "; then
    echo "Environment '$ENV_NAME' already exists. Updating it..."
else
    conda create -y -n "$ENV_NAME" python="$PYTHON_VERSION"
fi

# 3. Activate environment and install dependencies
echo "Activating environment and installing dependencies..."
conda activate "$ENV_NAME"

# Upgrade pip
pip install --upgrade pip

# Install project requirements
if [ -f "$PROJECT_ROOT/pamo_sql/requirements.txt" ]; then
    echo "Installing requirements from pamo_sql/requirements.txt..."
    pip install -r "$PROJECT_ROOT/pamo_sql/requirements.txt"
else
    echo "Warning: requirements.txt not found at $PROJECT_ROOT/pamo_sql/requirements.txt"
fi

echo ""
echo "================================================================="
echo "✅ Environment Setup Complete!"
echo "To activate the environment, run:"
echo ""
echo "    conda activate $ENV_NAME"
echo ""
echo "Note: You have an NVIDIA A100 80GB GPU. If you want to run local models,"
echo "you can install vLLM in this environment by running:"
echo "    pip install vllm"
echo "================================================================="
