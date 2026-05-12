#!/bin/bash
set -euo pipefail
LOG="$HOME/.hermes/logs/backup.cron-wrapper.log"
mkdir -p "$(dirname "$LOG")"
TS=$(date '+%F %T')
if OUT=$("$HOME/.hermes/scripts/backup-digital-corp.sh" 2>&1); then
  echo "$TS OK Hermes cron fallback backup completed" >> "$LOG"
  echo "$OUT" | tail -5 >> "$LOG"
  exit 0
else
  CODE=$?
  {
    echo "$TS ERROR Hermes cron fallback backup failed exit=$CODE"
    echo "$OUT" | sed -E 's/(sk-or-v1-|sk-proj-|xoxb-|xapp-)[A-Za-z0-9._:-]+/\1[REDACTED]/g; s/(TELEGRAM_BOT_TOKEN=).+/\1[REDACTED]/g; s/(OPENAI_API_KEY=).+/\1[REDACTED]/g; s/(OPENROUTER_API_KEY=).+/\1[REDACTED]/g; s/(ANTHROPIC_API_KEY=).+/\1[REDACTED]/g'
  } >> "$LOG"
  echo "Digital Corp backup failed. See $LOG"
  exit "$CODE"
fi
