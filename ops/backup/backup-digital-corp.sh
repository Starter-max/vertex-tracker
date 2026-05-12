#!/bin/bash
set -euo pipefail

CONFIG="$HOME/.hermes/backup-config.env"
DEFAULT_LOG="$HOME/.hermes/logs/backup.log"
mkdir -p "$(dirname "$DEFAULT_LOG")"

if [ ! -f "$CONFIG" ]; then
  echo "$(date '+%F %T') ERROR config not found: $CONFIG" >> "$DEFAULT_LOG"
  exit 1
fi

# shellcheck disable=SC1090
source "$CONFIG"

mkdir -p "$(dirname "$BACKUP_LOG")"
mkdir -p "$BACKUP_ROOT"

log() {
  echo "$(date '+%F %T') $*" >> "$BACKUP_LOG"
}

fail() {
  log "ERROR $*"
  exit 1
}

safe_grep_secret_diff() {
  grep -E "sk-|or-|xoxb-|xapp-|API_KEY|TOKEN|SECRET|TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|OPENROUTER_API_KEY|ANTHROPIC_API_KEY" >/dev/null 2>&1
}

log "backup started mode=$BACKUP_MODE"

if [ ! -d "$(dirname "$BACKUP_MARKER")" ]; then
  fail "backup disk mount missing: $(dirname "$BACKUP_MARKER")"
fi
if [ ! -f "$BACKUP_MARKER" ]; then
  fail "backup marker missing: $BACKUP_MARKER"
fi
if ! grep -q "$EXPECTED_MARKER_VALUE" "$BACKUP_MARKER"; then
  fail "wrong backup disk marker"
fi

FREE_KB=$(df -k "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
MIN_FREE_KB=$((10 * 1024 * 1024))
if [ "${FREE_KB:-0}" -lt "$MIN_FREE_KB" ]; then
  fail "not enough free space: ${FREE_KB}KB"
fi

TS=$(date '+%Y%m%d-%H%M%S')
WORKDIR=$(mktemp -d "/tmp/digital-corp-backup-$TS.XXXXXX")
ARCHIVE_NAME="digital-corp-backup-$TS.tar.gz"
ARCHIVE_PATH="$BACKUP_ROOT/$ARCHIVE_NAME"
MANIFEST_NAME="digital-corp-backup-$TS.manifest.txt"
MANIFEST_PATH="$BACKUP_ROOT/$MANIFEST_NAME"
SHA_PATH="$BACKUP_ROOT/digital-corp-backup-$TS.sha256"

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

mkdir -p "$WORKDIR/db-dumps" "$WORKDIR/meta"

{
  echo "# Git snapshot"
  echo "Date: $(date)"
  echo
  for REPO in "$SOURCE_DIGITAL_CORP" "$SOURCE_HERMES_HOME/hermes-agent"; do
    if [ -d "$REPO/.git" ]; then
      echo "## Repo: $REPO"
      git -C "$REPO" status --short || true
      git -C "$REPO" branch --show-current || true
      git -C "$REPO" remote -v | sed 's#://[^/@]*@#://***@#g' || true
      git -C "$REPO" log --oneline -5 || true
      echo
    else
      echo "GIT НЕ НАЙДЕН: $REPO"
    fi
  done
} > "$WORKDIR/meta/git-status.txt"

for REPO in "$SOURCE_DIGITAL_CORP" "$SOURCE_HERMES_HOME/hermes-agent"; do
  if [ -d "$REPO/.git" ]; then
    if ! git -C "$REPO" diff --quiet || ! git -C "$REPO" diff --cached --quiet; then
      if git -C "$REPO" diff | safe_grep_secret_diff; then
        log "DANGER possible secret in diff, skip auto commit for $REPO"
      else
        git -C "$REPO" add -u || true
        git -C "$REPO" commit -m "chore: auto snapshot before backup $TS" || true
      fi
    fi
  fi
done

if command -v pg_dump >/dev/null 2>&1; then
  pg_dump digitalcorp > "$WORKDIR/db-dumps/digitalcorp-$TS.sql" 2>>"$BACKUP_LOG" || log "postgres dump skipped or failed"
else
  log "pg_dump not found, postgres dump skipped"
fi

find "$SOURCE_HERMES_HOME" "$SOURCE_DIGITAL_CORP" -type f \( -name "*.sqlite" -o -name "*.db" \) \
  -not -path "*/node_modules/*" -not -path "*/.venv/*" -not -path "*/venv/*" 2>/dev/null > "$WORKDIR/meta/sqlite-files.txt" || true
while IFS= read -r DBFILE; do
  if [ -f "$DBFILE" ]; then
    BASENAME=$(basename "$DBFILE")
    cp "$DBFILE" "$WORKDIR/db-dumps/${BASENAME}.$TS.copy" || true
  fi
done < "$WORKDIR/meta/sqlite-files.txt"

{
  echo "# Digital Corp Backup Manifest"
  echo "Created at: $(date)"
  echo "Mode: $BACKUP_MODE"
  echo "Archive: $ARCHIVE_NAME"
  echo "Include secrets in local backup: $INCLUDE_SECRETS_IN_LOCAL_BACKUP"
  echo
  echo "## Sources"
  echo "$SOURCE_HERMES_HOME"
  echo "$SOURCE_DIGITAL_CORP"
  echo
  echo "## Disk"
  df -h "$BACKUP_ROOT"
  echo
  echo "## Source sizes"
  du -sh "$SOURCE_HERMES_HOME" 2>/dev/null || true
  du -sh "$SOURCE_DIGITAL_CORP" 2>/dev/null || true
  echo
  echo "## Meta"
  find "$WORKDIR/meta" -type f -maxdepth 1 -print | sort
  echo
  echo "## DB dumps/copies"
  find "$WORKDIR/db-dumps" -type f -maxdepth 1 -print | sort
} > "$MANIFEST_PATH"

TAR_EXCLUDES=(
  --exclude=".git"
  --exclude="node_modules"
  --exclude="venv"
  --exclude=".venv"
  --exclude="__pycache__"
  --exclude=".cache"
  --exclude="*.tmp"
  --exclude=".DS_Store"
  --exclude="digital-corp-backups"
  --exclude="backups/pre-backup-setup"
)

if [ "${INCLUDE_SECRETS_IN_LOCAL_BACKUP:-true}" != "true" ]; then
  TAR_EXCLUDES+=(--exclude=".env" --exclude=".env.*" --exclude="auth.json")
fi

tar "${TAR_EXCLUDES[@]}" -czf "$ARCHIVE_PATH" \
  "$SOURCE_HERMES_HOME" \
  "$SOURCE_DIGITAL_CORP" \
  "$WORKDIR/db-dumps" \
  "$WORKDIR/meta" \
  "$MANIFEST_PATH" \
  2>>"$BACKUP_LOG"

if [ ! -s "$ARCHIVE_PATH" ]; then
  fail "archive missing or empty: $ARCHIVE_PATH"
fi

tar -tzf "$ARCHIVE_PATH" >/dev/null 2>>"$BACKUP_LOG" || fail "archive integrity check failed"
shasum -a 256 "$ARCHIVE_PATH" > "$SHA_PATH"

cd "$BACKUP_ROOT"
ls -1t digital-corp-backup-*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | while IFS= read -r OLD; do
  rm -f "$OLD"
  rm -f "${OLD%.tar.gz}.sha256"
  rm -f "${OLD%.tar.gz}.manifest.txt"
  log "rotated old backup: $OLD"
done

COUNT=$(ls -1 digital-corp-backup-*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
log "backup completed archive=$ARCHIVE_NAME count=$COUNT"
echo "OK backup completed: $ARCHIVE_PATH"
