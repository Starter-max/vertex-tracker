# 110-known-limitations

1) Cron delivery по `deliver=telegram` без явного target ранее давал ошибку `no delivery target resolved`.
   - Обход: использовать конкретный target (например telegram DM) при критичных задачах.

2) В репозитории есть параллельные незакоммиченные изменения mental-flow-system.
   - Риск смешивания коммитов.
   - Мера: selective commit только inbox-файлов.

3) Dashboard backend файл содержит участки, требующие рефакторинга/санитарной проверки.
   - Сейчас не ломаем, работаем через подтверждённые API.

4) Потоки Redis corp:results/corp:alerts/corp:health могут отсутствовать до первого XADD.
   - Это нормальное состояние.

5) Approval flow пока частично инфраструктурный (БД+доки+события), UI-часть в dashboard inbox-блоке отложена.
