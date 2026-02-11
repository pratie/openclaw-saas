#!/bin/bash
# OpenClaw SaaS Startup Script

echo "🤖 Starting OpenClaw SaaS Platform..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: python3 -m venv ../venv"
    exit 1
fi

# Activate virtual environment
source ../venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Starting Flask server..."
echo ""
echo "🌐 Open your browser:"
echo "   → http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the app
python app.py
