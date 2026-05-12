#!/bin/bash
set -euo pipefail
cd /Volumes/256/digital-corp/dashboard/backend
export PATH="/Users/admin/.local/bin:/Volumes/256/digital-corp/dashboard/backend/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
exec /Volumes/256/digital-corp/dashboard/backend/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 3000
