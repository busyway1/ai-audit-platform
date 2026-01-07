#!/bin/bash
# Install dependencies for database migration scripts

echo "============================================"
echo "Installing Migration Dependencies"
echo "============================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found"
    echo "Creating venv..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install psycopg2-binary
echo ""
echo "Installing psycopg2-binary..."
pip install psycopg2-binary

# Install python-dotenv (should already be installed)
echo ""
echo "Installing python-dotenv..."
pip install python-dotenv

echo ""
echo "============================================"
echo "✅ Dependencies installed successfully!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. python apply_migration.py"
echo "2. python verify_schema.py"
