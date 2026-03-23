#!/bin/bash

# sit_mon backend startup script

set -e

echo "=========================================="
echo "sit_mon backend services"
echo "=========================================="
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Python version: $PYTHON_VERSION"

# Check if Rust is available for Python 3.13+
if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
    echo "Python 3.13+ detected - checking for Rust toolchain..."
    if ! command -v rustc &> /dev/null || ! command -v cargo &> /dev/null; then
        echo "Error: Python 3.13+ requires Rust to build pydantic-core"
        echo "Please install Rust first:"
        echo "  sudo apt-get install rustc cargo"
        exit 1
    fi
    echo "Rust toolchain found: $(rustc --version)"
fi

# Check if Redis is running
if ! command -v redis-cli &> /dev/null; then
    echo "Warning: redis-cli not found. Redis may not be installed."
    echo "The application will attempt to connect to Redis anyway."
else
    if ! redis-cli ping &> /dev/null; then
        echo "Warning: Redis is not running. Starting Redis..."
        redis-server --daemonize yes
        sleep 2
    fi
fi

# Determine venv directory (prefer .venv, fall back to venv)
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    VENV_DIR="venv"
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using default configuration."
    echo "Please create a .env file with your API credentials."
fi

# Start the application
echo ""
echo "Starting backend services..."
echo "API: http://0.0.0.0:8002"
echo "Docs: http://0.0.0.0:8002/docs"
echo "Health: http://0.0.0.0:8002/health"
echo "Batch reports: python3 generate_reports.py"
echo "Per-source reports:"
echo "  python3 generate_radio_report.py"
echo "  python3 generate_oil_rig_report.py"
echo "  python3 generate_power_grid_report.py"
echo "  python3 generate_maritime_report.py"
echo "Country power grid polls:"
echo "  python3 generate_power_grid_country_reports.py"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the application
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
