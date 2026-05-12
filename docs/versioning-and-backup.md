# Versioning and Backup

## Назначение
Этот контур защищает Цифровую Корпорацию от потери кода, конфигов, скилов, промтов, агентов, состояния системы и рабочих данных.

## Текущий статус
- Режим: TEMPORARY_BACKUP_MODE.
- Backup root: /Volumes/256/digital-corp-backups.
- Root marker: /Volumes/256/.digital-corp-backup-marker.
- Launchd-readable marker: /Volumes/256/digital-corp-backups/DIGITAL_CORP_BACKUP_MARKER.txt.
- Скрипт: /Users/admin/.hermes/scripts/backup-digital-corp.sh.
- Конфиг: /Users/admin/.hermes/backup-config.env.
- Лог: /Users/admin/.hermes/logs/backup.log.
- Ротация: максимум 5 архивов.
- Интервал launchd: 1800 секунд.

## Режимы

### TEMPORARY_BACKUP_MODE
Текущий режим. Бэкапы пишутся на внешний диск 256 ГБ.
Это временно: рабочие данные и бэкапы находятся слишком близко друг к другу.

### DEDICATED_BACKUP_DISK_MODE
Будущий режим. Бэкапы пишутся на отдельный внешний диск.
Рекомендуется APFS + шифрование.

## Git
В Git входят:
- код;
- скилы;
- агенты;
- промты;
- документация;
- миграции;
- скрипты;
- конфиги без секретов;
- .env.example;
- backup-config.example.env.

В Git не входят:
- .env;
- токены;
- auth.json;
- дампы;
- архивы;
- логи;
- кэш;
- node_modules;
- venv;
- .venv.

## Бэкапы
Каждый запуск:
1. Загружает /Users/admin/.hermes/backup-config.env.
2. Проверяет диск и маркер.
3. Проверяет свободное место.
4. Делает Git snapshot в meta/git-status.txt.
5. Копирует SQLite/DB файлы в db-dumps.
6. Создаёт manifest.
7. Создаёт tar.gz архив.
8. Проверяет архив через tar -tzf.
9. Создаёт sha256.
10. Удаляет старые архивы сверх MAX_BACKUPS=5.

## Проверка
Команды ручной проверки:

```bash
tail -100 /Users/admin/.hermes/logs/backup.log
ls -lah /Volumes/256/digital-corp-backups
LATEST=$(ls -1t /Volumes/256/digital-corp-backups/digital-corp-backup-*.tar.gz | head -1)
tar -tzf "$LATEST" >/dev/null && echo ARCHIVE_OK
shasum -a 256 "$LATEST"
launchctl list | grep com.digitalcorp.backup
```

## Восстановление
1. Найти последний архив.
2. Распаковать во временную папку.
3. Проверить структуру.
4. Восстановить рабочие папки только вручную после подтверждения владельца.
5. Не перетирать живую систему автоматически.

## Риски
- Текущий внешний диск 256 ГБ — временное решение.
- Если .env входит в архив, архив нельзя отправлять в облако без шифрования.
- 5 получасовых архивов дают только короткую историю.
- Git не заменяет полный бэкап.
- Архив не заменяет Git.
- На macOS launchd может требовать Full Disk Access / Removable Volumes permissions для доступа к /Volumes/256. Ручной запуск скрипта подтверждён, но автоматический launchd запуск сейчас упирается в Operation not permitted при чтении маркера.
- До исправления macOS permissions настроен временный Hermes cron fallback `digital-corp-backup-fallback-30m` каждые 30 минут. Он запускает тот же backup-скрипт без LLM, молчит при успехе и отправляет сообщение только при ошибке.
