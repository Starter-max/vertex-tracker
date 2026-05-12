#!/bin/bash
set -euo pipefail
export HOME=/Users/admin
export PATH=/Users/admin/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Volumes/256/digital-corp/dashboard/backend
printf '[%s] starting digital-corp dashboard via launchd wrapper\n' "$(date -Iseconds)" >> /Volumes/256/digital-corp/logs/dashboard.runner.log
exec /usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 3000
