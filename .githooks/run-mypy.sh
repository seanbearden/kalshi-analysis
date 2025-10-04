#!/usr/bin/env bash
# Pre-commit hook to run mypy from backend directory
# This ensures mypy can find the installed backend package

set -e

cd backend

# Check if mypy is available
if ! python3 -m mypy --version &> /dev/null; then
    echo "⚠️  mypy not found in local Python environment - skipping pre-commit check"
    echo "   (mypy will still run in GitHub Actions CI)"
    exit 0
fi

exec python3 -m mypy .
