# Launchd Backup Permission Fix

## Статус

`com.digitalcorp.backup` загружен и plist валиден, но macOS запрещает LaunchAgent читать marker-файлы на `/Volumes/256`.

Факт из strict audit:

```text
grep: /Volumes/256/.digital-corp-backup-marker: Operation not permitted
grep: /Volumes/256/digital-corp-backups/DIGITAL_CORP_BACKUP_MARKER.txt: Operation not permitted
```

## Почему это нельзя корректно исправить только из CLI

Это macOS TCC / Privacy & Security permission. Без действия владельца в GUI нельзя безопасно выдать Full Disk Access / Removable Volumes для LaunchAgent/shell-исполнителя.

## Что уже работает до исправления

Hermes cron fallback `digital-corp-backup-fallback-30m` работает каждые 30 минут и запускает тот же backup-скрипт без LLM.

## Что сделать владельцу

1. Открыть macOS System Settings.
2. Перейти в Privacy & Security.
3. Открыть Full Disk Access.
4. Добавить/включить доступ для:
   - Terminal.app;
   - `/bin/bash`, если macOS позволит добавить Unix executable;
   - Hermes/Python executable: `/Users/admin/.hermes/hermes-agent/venv/bin/python`;
   - при наличии пункта Removable Volumes — разрешить доступ к внешним томам.
5. Перезапустить backup LaunchAgent:

```bash
launchctl unload ~/Library/LaunchAgents/com.digitalcorp.backup.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.digitalcorp.backup.plist
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.backup
```

## Проверка PASS

```bash
plutil -lint ~/Library/LaunchAgents/com.digitalcorp.backup.plist
launchctl list | grep com.digitalcorp.backup
tail -100 ~/.hermes/logs/backup.launchd.err.log
tail -100 ~/.hermes/logs/backup.log
LATEST=$(ls -1t /Volumes/256/digital-corp-backups/digital-corp-backup-*.tar.gz | head -1)
test -s "$LATEST" && echo ARCHIVE_NOT_EMPTY
tar -tzf "$LATEST" >/dev/null && echo ARCHIVE_READABLE
test -f "${LATEST%.tar.gz}.sha256" && echo SHA_EXISTS
```

Критерий готовности:

- в `backup.launchd.err.log` больше нет `Operation not permitted` для marker-файла;
- после `kickstart` появляется новый архив;
- архив читается;
- SHA есть;
- COUNT архивов остаётся <= 5.
