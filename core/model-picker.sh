#!/bin/bash
# model-picker.sh — запускает model-picker.py и применяет модель
# Используется cron для ежедневного обновления

export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY /Volumes/256/digital-corp/core/.env | cut -d= -f2)

RESULT=$(python3 /Volumes/256/digital-corp/core/model-picker.py --apply 2>&1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] $RESULT" >> /Volumes/256/digital-corp/logs/model-picker.log

# Если модель изменилась — перезапустить gateway
MODEL=$(echo "$RESULT" | grep "^model=" | cut -d= -f2)
if [ -n "$MODEL" ]; then
    # Проверяем, изменилась ли модель
    CURRENT=$(grep "^  default:" ~/.hermes/config.yaml | awk '{print $2}')
    if [ "$MODEL" != "$CURRENT" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Model changed: $CURRENT -> $MODEL" >> /Volumes/256/digital-corp/logs/model-picker.log
        hermes gateway restart 2>/dev/null || true
    fi
fi
