#!/bin/bash
set -euo pipefail
cd /Volumes/256/digital-corp
export PATH="/Users/admin/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
exec /opt/homebrew/bin/python3.12 /Volumes/256/digital-corp/agents/a01-cost-controller/main.py
