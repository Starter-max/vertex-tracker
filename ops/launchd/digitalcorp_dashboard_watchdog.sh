#!/bin/bash
set -u
export HOME=/Users/admin
export PATH=/Users/admin/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
LABEL="com.digitalcorp.dashboard.runner"
PLIST="/Users/admin/Library/LaunchAgents/${LABEL}.plist"
LOG="/Users/admin/Library/Logs/digitalcorp-dashboard.watchdog.log"
URL="http://localhost:3000/api/system"
mkdir -p /Users/admin/Library/Logs
log(){ echo "[$(date -Iseconds)] $*" >> "$LOG"; }

# Keep required local containers up when Docker is available.
if command -v docker >/dev/null 2>&1; then
  for c in corp-postgres corp-redis; do
    state="$(docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null || echo missing)"
    if [ "$state" = "false" ]; then
      log "container $c stopped; starting"
      docker start "$c" >> "$LOG" 2>&1 || log "failed to start $c"
    elif [ "$state" = "missing" ]; then
      log "container $c missing"
    fi
  done
fi

if curl -fsS -m 5 "$URL" >/dev/null 2>&1; then
  exit 0
fi

log "dashboard healthcheck failed; restarting ${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}" >> "$LOG" 2>&1 || {
  log "kickstart failed; trying bootstrap"
  launchctl bootout "gui/$(id -u)" "$PLIST" >> "$LOG" 2>&1 || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST" >> "$LOG" 2>&1 || log "bootstrap failed"
}

for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if curl -fsS -m 3 "$URL" >/dev/null 2>&1; then
    log "dashboard recovered after ${i}s"
    exit 0
  fi
done
log "dashboard still unhealthy after restart attempt"
exit 1
