#!/bin/bash
set -e

echo "=== Stock Report Agent Setup ==="

# Check Python 3.11+
python3 --version

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env template if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env — please fill in your API keys before running."
else
    echo ".env already exists — skipping."
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: source .venv/bin/activate && python main.py --date 2026-05-23"
echo "  3. To schedule daily at 07:00 KST, add to crontab:"
echo "     0 7 * * 1-5 cd /Users/\$USER/stock-report-agent && source .venv/bin/activate && python main.py >> logs/report.log 2>&1"
