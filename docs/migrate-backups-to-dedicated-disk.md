# Migrate Backups to Dedicated Disk

## Когда выполнять
Когда владелец подключит отдельный backup-диск.

## Рекомендуемые параметры диска
- Объём: 1 ТБ или больше.
- Формат: APFS.
- Желательно: шифрование.
- Имя: DigitalCorpBackup.

## Шаги

1. Проверить диск:

```bash
ls -la /Volumes
df -h
```

2. Создать маркер:

```bash
cat > /Volumes/DigitalCorpBackup/.digital-corp-backup-marker <<'EOF'
DIGITAL_CORP_BACKUP_DISK=PRIMARY_BACKUP
MODE=DEDICATED_BACKUP_DISK_MODE
CREATED_FOR=Digital Corp Hermes Backup
EOF
```

3. Создать папку:

```bash
mkdir -p /Volumes/DigitalCorpBackup/backups
```

4. Перенести старые архивы:

```bash
rsync -avh /Volumes/256/digital-corp-backups/ /Volumes/DigitalCorpBackup/backups/
```

5. Обновить /Users/admin/.hermes/backup-config.env:

```bash
BACKUP_MODE=DEDICATED_BACKUP_DISK_MODE
BACKUP_ROOT=/Volumes/DigitalCorpBackup/backups
BACKUP_MARKER=/Volumes/DigitalCorpBackup/.digital-corp-backup-marker
EXPECTED_MARKER_VALUE=DIGITAL_CORP_BACKUP_DISK=PRIMARY_BACKUP
```

6. Проверить скрипт:

```bash
/Users/admin/.hermes/scripts/backup-digital-corp.sh
```

7. Перезапустить launchd:

```bash
launchctl unload /Users/admin/Library/LaunchAgents/com.digitalcorp.backup.plist
launchctl load /Users/admin/Library/LaunchAgents/com.digitalcorp.backup.plist
```

8. Сделать тест восстановления.

## Критерий готовности
- Новый диск подтверждён маркером.
- Архив создаётся на новом диске.
- Старые архивы перенесены.
- Ротация работает.
- Тест восстановления пройден.
- launchd имеет доступ к новому диску. Если macOS блокирует доступ, выдать Full Disk Access / Removable Volumes permission для shell/launchd-исполнителя или перенести backup root на разрешённый путь.
