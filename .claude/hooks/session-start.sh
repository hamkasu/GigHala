#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code on the web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "Installing GigHala Python dependencies..."

# Use --ignore-installed to avoid conflicts with Debian-managed system packages
# (e.g. cryptography is installed by Debian without a pip RECORD file)
pip install -r "$CLAUDE_PROJECT_DIR/requirements.txt" \
    --quiet \
    --ignore-installed \
    --no-warn-script-location 2>&1 | grep -v "^WARNING" || true

# Verify critical 2FA dependencies are importable
python3 -c "import pyotp, qrcode, flask, sqlalchemy" && \
    echo "✅ Core dependencies verified." || \
    echo "⚠️  Some dependencies may be missing — check pip output above."
