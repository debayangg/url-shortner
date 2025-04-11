#!/bin/bash

set -e  # Exit immediately if a command exits with non-zero status

# Activate virtual environment
echo "🔹 Activating virtual environment..."
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

# Export environment variables from .env
if [ -f .env ]; then
    echo "🔹 Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "⚠️  .env file not found! Skipping environment variable export."
fi

# Initialize SQLite database (only if it doesn't exist)
if [ ! -f "urls.db" ]; then
    echo "🔹 Initializing local SQLite database..."
    python -c "import database"
else
    echo "✅ SQLite database already exists."
fi

# Start the FastAPI server
echo "🚀 Starting FastAPI server on http://localhost:8000..."
uvicorn app:app --reload --host 0.0.0.0 --port 8000
