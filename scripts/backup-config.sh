#!/bin/bash
# Снимает слепок конфигов — без секретов
set -e

REPO="/Volumes/256/digital-corp"
mkdir -p "$REPO/infra/configs"

# Hermes config (убираем токены)
cp ~/.hermes/config.yaml "$REPO/infra/configs/hermes-config.yaml"
sed -i '' 's/token:.*$/token: REDACTED/g' "$REPO/infra/configs/hermes-config.yaml"
sed -i '' 's/api_key:.*$/api_key: REDACTED/g' "$REPO/infra/configs/hermes-config.yaml"

# .env template (структура без значений)
grep -oE '^[A-Z_]+=' /Volumes/256/digital-corp/core/.env | \
  sed 's/=/=YOUR_VALUE_HERE/' > "$REPO/infra/configs/env.template"

echo "Config backup done → infra/configs/"
