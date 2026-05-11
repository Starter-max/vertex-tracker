#!/bin/bash
echo "--- Health Check ---"
docker ps --format "  {{.Names}}: {{.Status}}" | grep -E "redis|postgres"
curl -sf http://localhost:3000/api/system > /dev/null && echo "  dashboard: OK" || echo "  dashboard: FAIL"
launchctl list | grep digitalcorp | awk '{print "  "$3": "$1}'
echo "---"
