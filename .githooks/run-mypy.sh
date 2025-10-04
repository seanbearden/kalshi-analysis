#!/usr/bin/env bash
# Pre-commit hook to run mypy from backend directory
# This ensures mypy can find the installed backend package

set -e

cd backend
exec python3 -m mypy .
