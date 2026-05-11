#!/bin/bash
# Откат к версии: ./scripts/rollback.sh v0.1.0
VERSION=${1:-""}
if [ -z "$VERSION" ]; then
  echo "Использование: ./scripts/rollback.sh <версия>"
  echo "Доступные версии:"; git tag --sort=-version:refname
  exit 1
fi

echo "=== Откат к $VERSION ==="
echo "1. Сохраняем текущее состояние..."
git stash

echo "2. Переключаемся на $VERSION..."
git checkout $VERSION

echo "3. Перезапускаем сервисы..."
pkill -f "uvicorn main:app" 2>/dev/null
sleep 1
cd /Volumes/256/digital-corp/dashboard/backend
nohup python3.12 -m uvicorn main:app --host 0.0.0.0 --port 3000 >> /Volumes/256/digital-corp/logs/dashboard.log 2>&1 &

launchctl unload ~/Library/LaunchAgents/com.digitalcorp.a01.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.digitalcorp.a01.plist

echo "4. Проверяем здоровье..."
sleep 3
bash /Volumes/256/digital-corp/scripts/health-check.sh

echo "=== Откат к $VERSION завершён ==="
