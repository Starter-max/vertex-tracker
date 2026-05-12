# Known Limitations

- Telegram quick commands are specified but not fully proven end-to-end in this pass.
- Cron Telegram delivery must be verified before daily morning brief can be considered live.
- Real A0x worker processes are not fully implemented; Redis stream provides integration point.
- Dashboard Inbox widget is backend-ready but not fully implemented in UI.
- Existing destructive kanban DELETE endpoint exists and must stay outside normal owner flow.
- Some system metrics still reference `/Volumes/256`; inbox runtime uses internal disk.
