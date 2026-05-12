#!/bin/bash
set -u
PLIST="$HOME/Library/LaunchAgents/com.digitalcorp.backup.plist"
ERR="$HOME/.hermes/logs/backup.launchd.err.log"
LOG="$HOME/.hermes/logs/backup.log"
BACKUP_DIR="/Volumes/256/digital-corp-backups"

echo "# Launchd backup PASS verifier"
echo "Date: $(date)"
echo

echo "## plist"
plutil -lint "$PLIST" || exit 1

echo

echo "## launchctl before"
launchctl list | grep com.digitalcorp.backup || true

echo

echo "## kickstart"
BEFORE=$(ls -1t "$BACKUP_DIR"/digital-corp-backup-*.tar.gz 2>/dev/null | head -1)
echo "BEFORE=${BEFORE:-NONE}"
launchctl kickstart -k "gui/$(id -u)/com.digitalcorp.backup" || true
sleep 8
AFTER=$(ls -1t "$BACKUP_DIR"/digital-corp-backup-*.tar.gz 2>/dev/null | head -1)
echo "AFTER=${AFTER:-NONE}"

echo

echo "## stderr tail sanitized"
tail -30 "$ERR" 2>/dev/null | sed -E 's/(sk-or-v1-|sk-proj-|xoxb-|xapp-)[A-Za-z0-9._:-]+/\1[REDACTED]/g' || true

echo

echo "## archive checks"
if [ -z "${AFTER:-}" ] || [ ! -s "$AFTER" ]; then
  echo "FAIL ARCHIVE_EMPTY_OR_MISSING"
  exit 2
fi
if tar -tzf "$AFTER" >/dev/null; then
  echo "PASS ARCHIVE_READABLE"
else
  echo "FAIL ARCHIVE_BROKEN"
  exit 3
fi
if [ -f "${AFTER%.tar.gz}.sha256" ]; then
  echo "PASS SHA_EXISTS"
else
  echo "FAIL SHA_MISSING"
  exit 4
fi
COUNT=$(ls -1 "$BACKUP_DIR"/digital-corp-backup-*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
echo "COUNT=$COUNT"
if [ "$COUNT" -le 5 ]; then
  echo "PASS ROTATION_OK"
else
  echo "FAIL ROTATION_TOO_MANY"
  exit 5
fi
if tail -80 "$ERR" 2>/dev/null | grep -q 'Operation not permitted'; then
  echo "BLOCKED STILL_HAS_OPERATION_NOT_PERMITTED"
  exit 6
fi
if [ "${BEFORE:-}" != "${AFTER:-}" ]; then
  echo "PASS NEW_ARCHIVE_CREATED_BY_LAUNCHD"
else
  echo "PARTIAL NO_NEW_ARCHIVE_DETECTED_CHECK_LOG_TIME"
fi

echo

echo "## backup log tail"
tail -20 "$LOG" 2>/dev/null || true
