# Ops Runbook: Dashboard Agents Layer

This runbook is for operating and troubleshooting the Digital Corp dashboard General Agents layer.

## Runtime location

Current expected repo:

```text
/Users/admin/digital-corp-runner-v2
```

Dashboard URL:

```text
http://localhost:3000
```

Prefer internal-disk runtime for active services. Do not assume `/Volumes/256` is the live runtime unless the active process/launchd plist proves it.

## Fast health check

From repo root:

```bash
curl -s http://localhost:3000/api/system
curl -s http://localhost:3000/api/agents | python3 -m json.tool
curl -s http://localhost:3000/api/kanban | python3 -m json.tool
curl -s http://localhost:3000/api/agents/stalls | python3 -m json.tool
```

Expected:

- `/api/system` returns JSON.
- `/api/agents` returns a list and includes `pepe`, `anton`, `katya`.
- `/api/kanban` returns a list with at least one agent-linked card.
- `/api/agents/stalls` returns an object with `threshold_minutes`, `count`, `items`.

## Full local smoke

```bash
python3 -m py_compile dashboard/backend/main.py dashboard/backend/parallel_engine.py scripts/verify_kanban_integrity.py
python3 tests/test_parallel_engine_unit.py
python3 scripts/verify_kanban_integrity.py
```

Expected:

- all unit tests print `PASS`;
- `verify_kanban_integrity.py` prints `OK kanban_integrity`.

## Restart dashboard safely

The dashboard is protected by launchd runner/watchdog on this setup.
Prefer launchd kickstart over ad-hoc long-lived shell wrappers.

```bash
launchctl kickstart -k gui/$(id -u)/com.digitalcorp.dashboard.runner
sleep 2
curl -s http://localhost:3000/api/system
```

If the dashboard still serves stale code:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
```

Then inspect the process cwd/command before killing anything. Do not kill unrelated services.

## Logs

Project-local logs are expected under:

```text
/Users/admin/digital-corp-runner-v2/Library/Logs
```

Launchd watchdog assets are versioned under:

```text
/Users/admin/digital-corp-runner-v2/ops/launchd
```

## Common issue: `/api/kanban` returns 500

Checklist:

1. Read the exact traceback from dashboard logs.
2. Verify migration columns exist on `kanban_cards`.
3. Verify JSON/JSONB fields are decoded through backend serialization helpers.
4. Verify the query does not depend on a table missing from live DB.

Known MVP design:

- skill matching currently uses `agents.skills` JSONB;
- it intentionally does not require an `agent_skills` table in live runtime.

Smoke after fix:

```bash
python3 scripts/verify_kanban_integrity.py
```

## Common issue: skill arrays are strings

Symptoms:

- frontend shows bracketed JSON as text;
- `matched_skills` or `missing_skills` are strings instead of arrays.

Fix pattern:

- ensure backend `_jsonable()` or equivalent decodes JSON/JSONB fields;
- add/keep smoke assertions in `scripts/verify_kanban_integrity.py`.

## Common issue: stalled-agent block breaks frontend

Expected endpoint shape:

```json
{
  "threshold_minutes": 120,
  "count": 0,
  "items": []
}
```

Frontend should not assume a raw list.

Smoke:

```bash
curl -s http://localhost:3000/api/agents/stalls | python3 -m json.tool
```

## Common issue: Telegram target resolution failed

Previously observed failure:

```text
deliver=telegram target resolved failed
```

Use explicit Kevin DM target where needed:

```text
telegram:Kevin (dm)
```

Before introducing new notification flows:

1. List cron jobs.
2. Find any job using generic `deliver=telegram`.
3. Update to explicit resolved target if needed.
4. Run or smoke-test the job.
5. Confirm no `target resolved failed` error.

## Parallel dispatcher operation

Dispatcher safe smoke:

```bash
curl -s -X POST http://localhost:3000/api/parallel/dispatcher/tick \
  -H 'Content-Type: application/json' \
  -d '{"limit":1}' | python3 -m json.tool
```

Expected:

- `ok: true`
- `launch_mode: claim_only`

Worker safe smoke:

```bash
curl -s -X POST http://localhost:3000/api/parallel/worker/tick \
  -H 'Content-Type: application/json' \
  -d '{"max_items":1,"allow_cli":false,"timeout_seconds":30}' | python3 -m json.tool
```

Expected:

- `ok: true`
- `mode: dry_run`
- `allow_cli: false`

Do not claim real execution until `allow_cli`/execution safety, budget controls, logging and rollback behavior are implemented and tested.

## Frontend validation

The dashboard frontend is a single Alpine.js file:

```text
dashboard/frontend/index.html
```

After edits, verify:

```bash
python3 - <<'PY'
from pathlib import Path
html = Path('dashboard/frontend/index.html').read_text()
print('templates_open', html.count('<template '))
print('templates_close', html.count('</template>'))
assert html.count('<template ') == html.count('</template>')
for marker in ['Генеральные агенты','agentFilterType','agentFilterProject','Пепе видит зависания','openAgentDirectChat']:
    assert marker in html, marker
print('OK frontend markers')
PY
```

Also verify from live server:

```bash
curl -s http://localhost:3000/ | grep -E 'Генеральные агенты|Пепе видит зависания' | head
```

## Git safety

Before declaring completion:

```bash
git status --short
git diff --stat
```

Then commit:

```bash
git add -A
git commit -m "feat: advance general agents dashboard integration"
```

Push only after smoke tests pass:

```bash
git push origin dev
```

If push is rejected because remote moved, fetch and inspect before rebasing. Do not hide unrelated conflict resolution inside this feature.

## Completion signal

After important terminal/dashboard work completes on macOS:

```bash
for i in 1 2 3; do afplay /System/Library/Sounds/Glass.aiff; sleep .25; done
```
