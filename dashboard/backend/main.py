from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from collections import defaultdict
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
import asyncpg, psutil, subprocess, asyncio, os, uuid, json, httpx, redis.asyncio as aioredis
from dotenv import load_dotenv
from company_builder import is_project_company_request, route_project_company, read_workroom
from parallel_engine import (
    ensure_parallel_migration,
    create_work_package,
    get_work_package,
    list_work_packages,
    update_subtask_status,
    dispatch_ready_subtasks,
    execute_running_subtasks,
    get_parallel_worker_status,
    emit_event,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)
load_dotenv(CORE_DIR / ".env", override=True)
DB = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": "localhost",
    "port": 5432,
}
FRONTEND = PROJECT_ROOT / "dashboard" / "frontend" / "index.html"
UPLOADS = PROJECT_ROOT / "dashboard" / "uploads"
UPLOADS.mkdir(exist_ok=True)
pool = None

async def apply_general_agents_migration():
    path = CORE_DIR / "migrations" / "007_general_agents.sql"
    if path.exists():
        async with pool.acquire() as c:
            await c.execute(path.read_text())

def _jsonable(row):
    d = dict(row)
    json_fields = {
        'mandate', 'restrictions', 'skills', 'metadata', 'required_skills',
        'matched_skills', 'missing_skills',
        'agent_status_snapshot', 'decision_options', 'tags'
    }
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif k in json_fields and isinstance(v, str):
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    return d

async def ensure_seeded():
    async with pool.acquire() as c:
        await c.execute("""
            INSERT INTO projects(id,name,type,status,budget_daily,budget_monthly)
            VALUES ('p04','Mental Flow System','personal','active',2.50,60.00)
            ON CONFLICT (id) DO NOTHING
        """)
        await c.execute("""
            INSERT INTO agents(id,project_id,name,role,status)
            VALUES
              ('p04-owner','p04','Owner','manager','configured'),
              ('p04-capture','p04','Capture Bot','capture','configured'),
              ('p04-review','p04','Review Bot','review','configured')
            ON CONFLICT (id) DO NOTHING
        """)
        await c.execute("""
            INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags)
            VALUES
              ('p04-sys-001','Mental Flow System MVP','Build the personal mental-flow app with capture, review, buckets, settings, admin users and Claude sorting.','feature','strategic','p04',NULL,'in_progress','P1',ARRAY['nextjs','pwa','claude']),
              ('p04-sys-002','Telegram admin bot','Add user management, edit flows, and owner onboarding for the bot.','feature','operational','p04',NULL,'planned','P1',ARRAY['telegram','admin'])
            ON CONFLICT (id) DO NOTHING
        """)
        await c.execute("""
            INSERT INTO settings(key,value,group_name,label)
            VALUES
              ('owner_mode','CEO / заказчик, не оператор','general','Режим владельца'),
              ('dashboard_entrypoint','/dashboard','general','Главная точка входа'),
              ('level0_goal','Верхний слой показывает субъектов работы: Пепе управляет, Антон строит, Катя собирает агентов и скилы. Каждое решение должно уменьшать экранное время владельца.','general','Цель уровня 0'),
              ('screen_time_rule','Любое решение проверять вопросом: уменьшает ли это время владельца у экрана? Если увеличивает ручной контроль, постоянный мониторинг или технические детали для владельца — решение плохое.','rules','Правило экранного времени'),
              ('owner_escalation_rules','Эскалировать владельцу только важное: риск денег, риск данных, продакшен, секреты, необратимые изменения, нехватка решения. Не тревожить владельца мелкими техническими шагами.','rules','Правила эскалации владельцу'),
              ('autonomous_execution_policy','Продолжать автономно до завершения задачи. Останавливаться только при серьёзном блокере, разрушительном действии, изменении секретов/.env, удалении данных, расходах сверх лимита или выкладке в продакшен.','rules','Автономное выполнение'),
              ('progress_blocks_policy','Во время длинной работы показывать короткие блоки: что делаю сейчас, что проверяю, какой результат. Не превращать владельца в оператора.','rules','Краткие прогресс-блоки'),
              ('completion_audio_signal','for i in 1 2 3; do afplay /System/Library/Sounds/Glass.aiff; sleep .25; done','rules','3 звуковых сигнала после важного terminal-завершения'),
              ('general_agents','pepe,anton,katya','agents','Стартовые генеральные агенты'),
              ('pepe_mandate','Пепе — управляющий Hermes: принимает задачи, классифицирует, назначает агентов, связывает с канбаном, контролирует зависания, эскалирует только важное.','agents','Мандат Пепе'),
              ('anton_mandate','Антон — внутренняя ИТ-компания: архитектура, backend, frontend, БД, интеграции, диагностика, тестирование, безопасность, документация и безопасный запуск.','agents','Мандат Антона'),
              ('katya_mandate','Катя — HR-компания агентов: роли, мандаты, ограничения, скилы, команды, подбор недостающих агентов и встройка новых компетенций.','agents','Мандат Кати'),
              ('agent_statuses','active, thinking, waiting, idle, error, paused','agents','Статусы агентов'),
              ('agent_stall_threshold_minutes','120','agents','Порог зависания агента, минут'),
              ('kanban_bidirectional_links','agent->task; task->agent; agent->skills; task->skills; chat->task; task->chat; activity_log->agent; activity_log->task','kanban','Двусторонние связи'),
              ('kanban_task_required_fields','assignedAgentId, curatorAgentId, requiredSkills, startedAt, nextStep, agentDiscussionId, agentStatusSnapshot, lastAgentActivityAt','kanban','Поля задачи для агентского слоя'),
              ('chat_vs_log_rule','Чат — коммуникация и решения. Журнал активности — факты действий. Не смешивать чат и журнал.','kanban','Правило чат/журнал'),
              ('telegram_delivery_target','telegram','notifications','Целевой канал Telegram'),
              ('telegram_delivery_guard','Перед запуском новых уведомлений проверять daily-cost-report: deliver=telegram target resolved failed. Новые чаты/уведомления не считать готовыми без рабочего target mapping.','notifications','Delivery guard Telegram'),
              ('daily_cost_report_status','known_issue_target_resolved_failed','notifications','Статус daily-cost-report'),
              ('daily_cost_report_schedule','ежедневно, cron job daily-cost-report','cron','Daily cost report'),
              ('daily_model_picker_schedule','ежедневно, cron job daily-model-picker','cron','Daily model picker'),
              ('git_auto_commit_schedule','cron job git-auto-commit','cron','Git auto-commit'),
              ('default_daily_budget_usd','2.50','budget','Старый дневной бюджет по умолчанию'),
              ('default_monthly_budget_usd','60.00','budget','Старый месячный бюджет по умолчанию'),
              ('cost_controller_agent','A01 cost controller','budget','Контроллер расходов'),
              ('hermes_model_fast','google/gemini-2.0-flash-free','hermes','Быстрая модель'),
              ('hermes_model_powerful','openrouter/owl-alpha','hermes','Сильная модель'),
              ('hermes_features_level0','skills, memory, delegation, profiles, webhooks, MCP, kanban, cron, Telegram gateway','hermes','Доступные механики Hermes'),
              ('hermes_cli_path','/Users/admin/.local/bin/hermes','hermes','Путь Hermes CLI'),
              ('core_services_disk_policy','Core services/projects should run from internal disk; external /Volumes/256 mainly for capacity expansion and large storage.','system','Политика диска'),
              ('dashboard_port','3000','system','Порт dashboard'),
              ('postgres_container','corp-postgres','system','PostgreSQL контейнер'),
              ('redis_container','corp-redis','system','Redis контейнер'),
              ('no_env_without_confirmation','true','safety','Не менять .env без подтверждения'),
              ('no_delete_data_without_confirmation','true','safety','Не удалять данные без подтверждения'),
              ('no_schema_change_without_migration','true','safety','Схема БД только миграцией'),
              ('no_prod_deploy_without_confirmation','true','safety','Продакшен только после подтверждения'),
              ('no_secret_exposure','true','safety','Не показывать секреты в UI')
            ON CONFLICT (key) DO UPDATE
            SET group_name=EXCLUDED.group_name,
                label=EXCLUDED.label,
                value=COALESCE(NULLIF(settings.value,''), EXCLUDED.value),
                updated_at=NOW()
        """)

class WsManager:
    def __init__(self): self.active = []
    async def connect(self, ws):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, data):
        for ws in list(self.active):
            try: await ws.send_json(data)
            except: self.active.remove(ws)

wsman = WsManager()

@asynccontextmanager
async def lifespan(app):
    global pool
    pool = await asyncpg.create_pool(**DB, min_size=2, max_size=10)
    await apply_general_agents_migration()
    await ensure_parallel_migration(pool, CORE_DIR / "migrations")
    await ensure_seeded()
    yield
    await pool.close()

app = FastAPI(title="Digital Corp", version="1.1.0", lifespan=lifespan)

@app.get("/api/system")
async def system_metrics():
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage('/Volumes/256')
        disk_pct, disk_free = round(disk.percent,1), f"{disk.free/(1024**3):.0f}GB свободно"
    except:
        disk_pct, disk_free = 0, "н/д"
    try:
        r = subprocess.run(['docker','ps','--format','{{.Names}}\t{{.Status}}'], capture_output=True, text=True, timeout=5)
        containers = {n: ('up' if 'Up' in s else 'down') for line in r.stdout.strip().split('\n') if '\t' in line for n, s in [line.split('\t',1)]}
    except: containers = {}
    try:
        lctl = subprocess.run(['launchctl','list'], capture_output=True, text=True, timeout=5)
        launchctl_out = lctl.stdout
        proc_names = []
        for p in psutil.process_iter(['name', 'cmdline']):
            cmdline = p.info.get('cmdline') or []
            if isinstance(cmdline, (list, tuple)):
                cmdline = " ".join(str(part) for part in cmdline)
            proc_names.append(f"{p.info.get('name') or ''} {cmdline}")
        proc_text = "\n".join(proc_names)
        services = {
            'hermes': 'hermes' in launchctl_out or 'hermes_cli.main' in proc_text,
            'a01': 'a01' in launchctl_out or 'a01-cost-controller' in proc_text,
        }
    except: services = {}
    return {"cpu": round(cpu,1), "ram_gb": round(mem.used/(1024**3),1),
            "ram_total": round(mem.total/(1024**3),1), "ram_pct": round(mem.percent,1),
            "disk_pct": disk_pct, "disk_free": disk_free,
            "containers": containers, "services": services, "ts": datetime.now().isoformat()}

@app.get("/api/projects")
async def get_projects():
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM projects ORDER BY type, id")
        costs = await c.fetch("""
            SELECT project_id, ROUND(SUM(cost_usd)::numeric,6) as usd,
                   COUNT(*) as calls, MAX(created_at) as last_call
            FROM costs WHERE created_at > NOW()-INTERVAL '24h' GROUP BY project_id
        """)
    cm = {r['project_id']: r for r in costs}
    return [{**dict(p),
             'cost_today': float(cm[p['id']]['usd']) if p['id'] in cm else 0.0,
             'calls_today': int(cm[p['id']]['calls']) if p['id'] in cm else 0,
             'last_activity': cm[p['id']]['last_call'].isoformat() if p['id'] in cm and cm[p['id']]['last_call'] else None}
            for p in rows]

@app.get("/api/projects/{pid}")
async def get_project(pid: str):
    async with pool.acquire() as c:
        p = await c.fetchrow("SELECT * FROM projects WHERE id=$1", pid)
        if not p: raise HTTPException(404)
        agents = await c.fetch("""
            SELECT agent_id, ROUND(SUM(cost_usd)::numeric,6) as usd, COUNT(*) as calls
            FROM costs WHERE project_id=$1 AND created_at > NOW()-INTERVAL '24h'
            GROUP BY agent_id ORDER BY usd DESC
        """, pid)
        total = await c.fetchval("SELECT ROUND(SUM(cost_usd)::numeric,6) FROM costs WHERE project_id=$1 AND created_at > NOW()-INTERVAL '24h'", pid)
        all_agents = await c.fetch("SELECT id, project_id, name, role, status, last_heartbeat FROM agents WHERE project_id=$1 ORDER BY id", pid)
    log_path = LOGS_DIR / f"{pid}.log"
    logs = "\n".join(log_path.read_text().splitlines()[-40:]) if log_path.exists() else "нет логов"
    return {**dict(p), "cost_today": float(total or 0), "agents": [dict(a) for a in agents], "project_agents": [dict(a) for a in all_agents], "logs": logs}

@app.post("/api/projects/{pid}/pause")
async def pause_proj(pid: str):
    async with pool.acquire() as c: await c.execute("UPDATE projects SET status='paused' WHERE id=$1", pid)
    await wsman.broadcast({"type":"project_update","id":pid,"status":"paused"}); return {"ok":True}

@app.post("/api/projects/{pid}/start")
async def start_proj(pid: str):
    async with pool.acquire() as c: await c.execute("UPDATE projects SET status='active' WHERE id=$1", pid)
    await wsman.broadcast({"type":"project_update","id":pid,"status":"active"}); return {"ok":True}

class BudgetBody(BaseModel): daily: float; monthly: float = 0

@app.put("/api/projects/{pid}/budget")
async def update_budget(pid: str, b: BudgetBody):
    async with pool.acquire() as c: await c.execute("UPDATE projects SET budget_daily=$1, budget_monthly=$2 WHERE id=$3", b.daily, b.monthly, pid)
    return {"ok":True}

@app.get("/api/costs/today")
async def costs_today():
    async with pool.acquire() as c:
        total = await c.fetchval("SELECT ROUND(SUM(cost_usd)::numeric,6) FROM costs WHERE created_at > NOW()-INTERVAL '24h'")
    return {"total": float(total or 0)}

@app.get("/api/settings")
async def get_settings():
    async with pool.acquire() as c: rows = await c.fetch("SELECT * FROM settings ORDER BY group_name, key")
    groups = defaultdict(list)
    for r in rows: groups[r['group_name']].append(dict(r))
    return dict(groups)

class SettingBody(BaseModel): value: str

@app.put("/api/settings/{key}")
async def update_setting(key: str, body: SettingBody):
    async with pool.acquire() as c: await c.execute("UPDATE settings SET value=$1, updated_at=NOW() WHERE key=$2", body.value, key)
    return {"ok":True}

@app.get("/api/knowledge")
async def get_knowledge():
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM knowledge_items ORDER BY freshness_score ASC, category, name")
    items = [dict(r) for r in rows]
    total = len(items) or 1
    summary = {
        "total": len(items),
        "ok": len([i for i in items if i.get('status') == 'ok']),
        "outdated": len([i for i in items if i.get('status') == 'outdated']),
        "critical": len([i for i in items if i.get('status') == 'critical']),
        "unknown": len([i for i in items if i.get('status') == 'unknown']),
        "avg_score": round(sum(i.get('freshness_score') or 0 for i in items) / total),
    }
    return {"items": items, "summary": summary}

@app.post("/api/knowledge/refresh")
async def refresh_knowledge():
    subprocess.Popen([
        "python3.12",
        str(PROJECT_ROOT / "agents" / "a06-research" / "research_agent.py"),
    ], stdout=open(LOGS_DIR / "a06.log", "a"), stderr=subprocess.STDOUT)
    return {"ok": True}

from typing import Optional, List

class KanbanCardBody(BaseModel):
    title: str
    description: str = ""
    card_type: str = "task"
    layer: str = "strategic"
    project_id: Optional[str] = None
    agent_id: Optional[str] = None
    status: str = "planned"
    priority: str = "P2"
    due_date: Optional[str] = None
    tags: List[str] = []

class StatusBody(BaseModel):
    status: str

class ParallelWorkPackageBody(BaseModel):
    title: str
    objective: str = ""
    project_id: Optional[str] = "corp"
    priority: str = "P2"
    parallel_limit: int = 3
    backup_ref: Optional[str] = None
    diagnostic_ref: Optional[str] = None
    kanban_card_id: Optional[str] = None
    subtasks: List[dict] = []
    metadata: dict = {}

class SubtaskStatusBody(BaseModel):
    status: str
    result_summary: Optional[str] = None
    error_summary: Optional[str] = None

class ParallelDispatcherTickBody(BaseModel):
    work_package_id: Optional[str] = None
    limit: Optional[int] = None

class ParallelWorkerTickBody(BaseModel):
    work_package_id: Optional[str] = None
    max_items: int = 1
    allow_cli: bool = False
    timeout_seconds: int = 120


def _skill_summary_from_path(path: Path):
    text = path.read_text(errors="ignore")
    lines = text.splitlines()
    name = path.parent.name
    desc = ""
    in_frontmatter = lines[:1] == ["---"]
    for line in lines[:80]:
        if line.startswith("name:"):
            name = line.split(":",1)[1].strip().strip('"') or name
        elif line.startswith("description:"):
            desc = line.split(":",1)[1].strip().strip('"')
    return {"id": name, "name": name, "description": desc, "path": str(path)}

@app.get("/api/skills")
async def list_skills():
    roots = [Path("/Users/admin/.hermes/skills"), PROJECT_ROOT / "skills"]
    out = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for md in root.rglob("SKILL.md"):
            item = _skill_summary_from_path(md)
            if item["name"] not in seen:
                seen.add(item["name"]); out.append(item)
    return sorted(out, key=lambda x: x["name"])

@app.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str):
    safe = skill_name.replace("..", "").replace("/", "").replace("\\", "")
    for root in [Path("/Users/admin/.hermes/skills"), PROJECT_ROOT / "skills"]:
        if not root.exists():
            continue
        for md in root.rglob("SKILL.md"):
            item = _skill_summary_from_path(md)
            if item["name"] == safe or md.parent.name == safe:
                return {**item, "content": md.read_text(errors="ignore")[:20000]}
    raise HTTPException(404, "skill not found")

@app.get("/api/parallel/work-packages")
async def api_parallel_list(status: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50):
    return await list_work_packages(pool, status=status, project_id=project_id, limit=min(limit, 200))

@app.post("/api/parallel/work-packages")
async def api_parallel_create(body: ParallelWorkPackageBody):
    data = body.dict()
    if not data.get("objective"):
        data["objective"] = data.get("title") or "Parallel work package"
    return await create_work_package(pool, REDIS_URL, data)

@app.post("/api/parallel/dispatcher/tick")
async def api_parallel_dispatcher_tick(body: ParallelDispatcherTickBody = ParallelDispatcherTickBody()):
    safe_limit = body.limit
    if safe_limit is not None:
        safe_limit = max(1, min(int(safe_limit), 10))
    return await dispatch_ready_subtasks(pool, REDIS_URL, work_package_id=body.work_package_id, limit=safe_limit)

@app.post("/api/parallel/worker/tick")
async def api_parallel_worker_tick(body: ParallelWorkerTickBody = ParallelWorkerTickBody()):
    safe_max_items = max(1, min(int(body.max_items or 1), 5))
    safe_timeout = max(15, min(int(body.timeout_seconds or 120), 600))
    return await execute_running_subtasks(
        pool,
        REDIS_URL,
        work_package_id=body.work_package_id,
        max_items=safe_max_items,
        allow_cli=bool(body.allow_cli),
        timeout_seconds=safe_timeout,
    )

@app.get("/api/parallel/worker/status")
async def api_parallel_worker_status(work_package_id: Optional[str] = None):
    return await get_parallel_worker_status(pool, REDIS_URL, work_package_id=work_package_id)

@app.get("/api/parallel/work-packages/{work_package_id}")
async def api_parallel_get(work_package_id: str):
    item = await get_work_package(pool, work_package_id)
    if not item:
        raise HTTPException(404, "work package not found")
    return item

@app.patch("/api/parallel/subtasks/{subtask_id}/status")
async def api_parallel_subtask_status(subtask_id: str, body: SubtaskStatusBody):
    item = await update_subtask_status(pool, REDIS_URL, subtask_id, body.status, body.result_summary, body.error_summary)
    if not item:
        raise HTTPException(404, "subtask not found")
    return item

@app.post("/api/parallel/work-packages/{work_package_id}/events")
async def api_parallel_event(work_package_id: str, body: dict):
    return await emit_event(
        pool,
        REDIS_URL,
        str(body.get("event_type") or "note"),
        str(body.get("message") or "parallel event"),
        work_package_id,
        subtask_id=body.get("subtask_id"),
        agent_id=body.get("agent_id"),
        severity=str(body.get("severity") or "info"),
        payload=body.get("payload") or {},
    )

@app.get("/api/kanban")
async def get_kanban(layer: str = "strategic", project_id: str = None, card_type: str = None):
    """Kanban cards enriched with agent and skill links for the CEO dashboard."""
    async with pool.acquire() as c:
        q = """
            SELECT
                kc.*,
                COALESCE(kc.assigned_agent_id, kc.agent_id) AS effective_assigned_agent_id,
                a.name AS assigned_agent_name,
                a.status AS assigned_agent_status,
                a.last_activity_at AS assigned_agent_last_activity_at,
                ca.name AS curator_agent_name,
                COALESCE(skill_calc.matched_skills, '[]'::jsonb) AS matched_skills,
                COALESCE(skill_calc.missing_skills, '[]'::jsonb) AS missing_skills
            FROM kanban_cards kc
            LEFT JOIN agents a ON a.id = COALESCE(kc.assigned_agent_id, kc.agent_id)
            LEFT JOIN agents ca ON ca.id = kc.curator_agent_id
            LEFT JOIN LATERAL (
                WITH required AS (
                    SELECT jsonb_array_elements_text(COALESCE(kc.required_skills, '[]'::jsonb)) AS skill_id
                ), agent_skill_rows AS (
                    SELECT jsonb_array_elements_text(COALESCE(a.skills, '[]'::jsonb)) AS skill_id
                )
                SELECT
                    COALESCE(jsonb_agg(required.skill_id) FILTER (WHERE agent_skill_rows.skill_id IS NOT NULL), '[]'::jsonb) AS matched_skills,
                    COALESCE(jsonb_agg(required.skill_id) FILTER (WHERE agent_skill_rows.skill_id IS NULL), '[]'::jsonb) AS missing_skills
                FROM required
                LEFT JOIN agent_skill_rows USING (skill_id)
            ) skill_calc ON TRUE
            WHERE kc.layer=$1
        """
        params = [layer]
        if project_id:
            q += f" AND kc.project_id=${len(params)+1}"
            params.append(project_id)
        if card_type:
            q += f" AND kc.card_type=${len(params)+1}"
            params.append(card_type)
        rows = await c.fetch(q + " ORDER BY kc.priority, kc.moved_at ASC", *params)
    cards = []
    now = datetime.now().astimezone()
    for r in rows:
        d = _jsonable(r)
        moved_at = r.get('moved_at')
        if moved_at:
            delta = now - moved_at
            hrs = int(delta.total_seconds() // 3600)
            d['time_in_stage_hrs'] = hrs
            d['time_in_stage'] = f"{hrs}ч" if hrs < 48 else f"{hrs//24}д"
        else:
            d['time_in_stage_hrs'] = 0
            d['time_in_stage'] = '—'
        last_agent_activity = r.get('assigned_agent_last_activity_at') or r.get('last_agent_activity_at')
        agent_activity_heat = 0
        agent_activity_state = 'unknown'
        if last_agent_activity:
            activity_delta = now - last_agent_activity
            activity_minutes = int(activity_delta.total_seconds() // 60)
            if activity_minutes <= 15:
                agent_activity_heat = 3
                agent_activity_state = 'hot'
            elif activity_minutes <= 60:
                agent_activity_heat = 2
                agent_activity_state = 'warm'
            elif activity_minutes <= 180:
                agent_activity_heat = 1
                agent_activity_state = 'cool'
            else:
                agent_activity_heat = 0
                agent_activity_state = 'stale'
            d['agent_activity_age_minutes'] = activity_minutes
        d['agent_activity_heat'] = agent_activity_heat
        d['agent_activity_state'] = agent_activity_state
        cards.append(d)
    return cards

@app.post("/api/kanban")
async def create_kanban_card(body: KanbanCardBody):
    cid = f"card-{int(datetime.now().timestamp())}"
    async with pool.acquire() as c:
        await c.execute("""
            INSERT INTO kanban_cards (id,title,description,card_type,layer,project_id,agent_id,status,priority,due_date,tags)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """, cid, body.title, body.description, body.card_type, body.layer, body.project_id, body.agent_id, body.status, body.priority, body.due_date, body.tags)
    return {"ok": True, "id": cid}

@app.patch("/api/kanban/{card_id}/status")
async def update_kanban_status(card_id: str, body: StatusBody):
    async with pool.acquire() as c:
        card = await c.fetchrow("SELECT * FROM kanban_cards WHERE id=$1", card_id)
        if not card: raise HTTPException(404, "card not found")
        await c.execute("""
            UPDATE kanban_cards
            SET status=$1,
                moved_at=NOW(),
                updated_at=NOW(),
                started_at=CASE WHEN $1='in_progress' THEN COALESCE(started_at,NOW()) ELSE started_at END,
                last_agent_activity_at=NOW(),
                agent_status_snapshot=jsonb_build_object('agent', COALESCE(assigned_agent_id, agent_id), 'status', $1, 'updated_at', NOW())
            WHERE id=$2
        """, body.status, card_id)
        agent_id = card['assigned_agent_id'] or card['agent_id']
        if agent_id:
            agent_status = {'in_progress':'active','review':'waiting','blocked':'error','done':'idle','queue':'waiting','planned':'waiting','frozen':'paused'}.get(body.status, 'active')
            event_type = {'in_progress':'task_started','review':'status_changed','blocked':'task_blocked','done':'task_completed','queue':'status_changed','planned':'status_changed','frozen':'task_paused'}.get(body.status, 'status_changed')
            await c.execute("""
                UPDATE agents
                SET status=$1,
                    current_task_id=CASE WHEN $2='done' AND current_task_id=$3 THEN NULL ELSE COALESCE(current_task_id,$3) END,
                    active_since=CASE WHEN $2='in_progress' THEN COALESCE(active_since,NOW()) ELSE active_since END,
                    last_activity_at=NOW(), updated_at=NOW()
                WHERE id=$4
            """, agent_status, body.status, card_id, agent_id)
            await c.execute("""
                INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                VALUES($1,$2,$3,$4,$5,$6)
            """, "log-" + str(uuid.uuid4())[:12], agent_id, event_type, card_id, card['project_id'], f"Статус задачи изменён на {body.status}")
    return {"ok": True}

@app.delete("/api/kanban/{card_id}")
async def delete_kanban_card(card_id: str):
    async with pool.acquire() as c:
        await c.execute("DELETE FROM kanban_cards WHERE id=$1", card_id)
    return {"ok": True}

@app.get("/api/chat/sessions")
async def chat_sessions():
    async with pool.acquire() as c: rows = await c.fetch("SELECT * FROM chat_sessions ORDER BY created_at DESC LIMIT 20")
    return [dict(r) for r in rows]

class NewSession(BaseModel): name: str = "Новый чат"

@app.post("/api/chat/sessions")
async def new_session(body: NewSession):
    sid = str(uuid.uuid4())[:8]
    async with pool.acquire() as c: await c.execute("INSERT INTO chat_sessions(id,name) VALUES($1,$2)", sid, body.name)
    return {"id": sid, "name": body.name}

@app.get("/api/chat/sessions/{sid}/messages")
async def get_chat_messages(sid: str):
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM chat_messages WHERE session_id=$1 ORDER BY created_at ASC LIMIT 200", sid)
    return [dict(r) for r in rows]

@app.delete("/api/chat/sessions/{sid}")
async def delete_chat_session(sid: str):
    async with pool.acquire() as c:
        await c.execute("DELETE FROM chat_messages WHERE session_id=$1", sid)
        await c.execute("DELETE FROM chat_sessions WHERE id=$1", sid)
    return {"ok": True}

class MsgBody(BaseModel): session_id: str; content: str

def _clean_hermes_output(out: str) -> str:
    text = out or ""
    # Hermes CLI may echo the whole prompt before the visual answer box. Keep only the final box/content.
    if "╭─ ⚕ Hermes" in text:
        text = text.split("╭─ ⚕ Hermes")[-1]
    lines = [ln.rstrip() for ln in text.splitlines()]
    cleaned = []
    skip_prefixes = (
        "Query:", "Initializing agent", "Resume this session with:",
        "Session:", "Duration:", "Messages:", "Tool Calls:", "MCP Tools:",
        "hermes --resume", "╰", "╭", "─",
    )
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in skip_prefixes):
            continue
        if "hermes --resume" in s:
            continue
        if set(s) <= {"─", "╭", "╮", "╰", "╯", "│", " ", "⚕"}:
            continue
        # Strip box borders and indentation from Hermes' rendered answer.
        s = s.strip(" │")
        if s:
            cleaned.append(s)
    return "\n".join(cleaned).strip()

async def call_hermes(message: str, session_id: str) -> str:
    """Call Hermes from the dashboard backend. Never fail silently."""
    hermes_port = os.getenv("HERMES_PORT", "8000")
    last_error = ""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for path in ["/api/chat", "/chat", "/v1/chat/completions"]:
                try:
                    r = await client.post(
                        f"http://localhost:{hermes_port}{path}",
                        json={"message": message, "session_id": session_id},
                    )
                    if r.status_code == 200:
                        d = r.json()
                        response = d.get("response") or d.get("content") or d.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if response:
                            return str(response)[:4000]
                    else:
                        last_error = f"HTTP {path}: {r.status_code}"
                except Exception as e:
                    last_error = f"HTTP {path}: {type(e).__name__}: {e}"
    except Exception as e:
        last_error = f"HTTP client: {type(e).__name__}: {e}"

    try:
        r = subprocess.run(
            ["/Users/admin/.local/bin/hermes", "chat", "-q", message],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "PATH": "/Users/admin/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"},
        )
        out = _clean_hermes_output(r.stdout)
        if r.returncode == 0 and out:
            return out[:4000]
        last_error = f"CLI rc={r.returncode}; stderr={(r.stderr or '')[-500:]}"
    except Exception as e:
        last_error = f"CLI: {type(e).__name__}: {e}"

    return "⚠️ Hermes не ответил. Я зафиксировал сбой в журнале; причина: " + last_error[:700]

AGENT_PERSONAS = {
    "pepe": {
        "name": "Пепе",
        "role": "управляющий цифровой корпорации Hermes",
        "style": "коротко координирует, назначает ответственных, формулирует следующий шаг и эскалирует только важное",
    },
    "anton": {
        "name": "Антон",
        "role": "внутренняя ИТ-компания: backend, frontend, БД, интеграции, диагностика, тестирование",
        "style": "говорит технически, но понятно владельцу; предлагает проверяемые действия и безопасный запуск",
    },
    "katya": {
        "name": "Катя",
        "role": "HR-компания агентов: роли, мандаты, скилы, команды и встройка компетенций",
        "style": "проверяет зоны ответственности, недостающие скилы и кого лучше назначить",
    },
}

def _fallback_agent_reply(agent_id: str, owner_text: str) -> str:
    fallback = {
        "pepe": "Принял. Я фиксирую запрос, связываю его с рабочим потоком и определяю ответственного. Следующий шаг: удержать задачу в движении без лишнего участия владельца.",
        "anton": "Принял. Проверяю техническую часть: API, логи, базу, UI и связки. Следующий шаг: воспроизвести проблему, исправить и подтвердить тестом.",
        "katya": "Приняла. Проверяю роли, мандаты и недостающие скилы. Следующий шаг: определить, кто должен вести задачу и какие компетенции нужны.",
    }
    return fallback.get(agent_id, "Принял сообщение. Фиксирую его и готовлю следующий шаг.")

async def _agent_reply(agent_id: str, owner_text: str, chat_title: str, task_id: str = None, project_id: str = None) -> str:
    persona = AGENT_PERSONAS.get(agent_id, {"name": agent_id, "role": "агент Digital Corp", "style": "отвечает кратко и по делу"})
    prompt = f"""
Ты отвечаешь внутри dashboard Digital Corp как агент {persona['name']}.
Роль: {persona['role']}.
Стиль: {persona['style']}.
Философия: владелец — CEO/заказчик, не оператор; каждое решение должно уменьшать его экранное время.
Чат: {chat_title}.
Связанная задача: {task_id or 'нет'}.
Проект: {project_id or 'corp'}.
Сообщение владельца: {owner_text}

Ответь от первого лица как {persona['name']}. Не говори, что ты языковая модель. Дай короткий рабочий ответ: что понял, что делаешь/предлагаешь, следующий шаг. Если нужен другой агент, явно упомяни его.
""".strip()
    response = await call_hermes(prompt, f"agent-{agent_id}-{task_id or 'general'}")
    if response.startswith("⚠️ Hermes не ответил"):
        fallback = {
            "pepe": "Принял. Я фиксирую запрос, связываю его с канбаном и определяю ответственного. Следующий шаг: проверить, нужен ли Антон для техники или Катя для ролей/скилов.",
            "anton": "Принял. Проверяю техническую часть: API, логи, базу, UI и связку с канбаном. Следующий шаг: воспроизвести проблему и дать исправление с проверкой.",
            "katya": "Приняла. Проверяю, кто должен выполнять задачу, какие скилы нужны и нет ли разрыва между ролью агента и фактической работой.",
        }.get(agent_id, "Принял сообщение. Фиксирую его и готовлю следующий шаг.")
        return fallback + "\n\n" + response
    return response

async def _insert_agent_message(c, chat_id: str, sender_id: str, text: str, message_type: str, task_id: str = None, project_id: str = None):
    mid = "msg-" + str(uuid.uuid4())[:12]
    await c.execute("""
        INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id)
        VALUES($1,$2,'agent',$3,$4,$5,$6,$7)
    """, mid, chat_id, sender_id, text, message_type, task_id, project_id)
    await c.execute("""
        INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
        VALUES($1,$2,'message_sent',$3,$4,$5)
    """, "log-" + str(uuid.uuid4())[:12], sender_id, task_id, project_id, f"{sender_id} ответил в чате {chat_id}: {text[:180]}")
    await c.execute("UPDATE agents SET last_activity_at=NOW(), updated_at=NOW(), status=CASE WHEN status='idle' THEN 'active' ELSE status END WHERE id=$1", sender_id)
    return mid

@app.post("/api/chat/send")
async def send_msg(body: MsgBody):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO chat_messages(session_id,role,content) VALUES($1,'user',$2)", body.session_id, body.content)
    if is_project_company_request(body.content):
        routed = await route_project_company(pool, REDIS_URL, body.content, source='dashboard_chat')
        response = routed.get('response', str(routed))
    else:
        response = await call_hermes(body.content, body.session_id)
    async with pool.acquire() as c:
        await c.execute("INSERT INTO chat_messages(session_id,role,content) VALUES($1,'assistant',$2)", body.session_id, response)
    await wsman.broadcast({"type":"chat","session_id":body.session_id,"role":"assistant","content":response})
    return {"ok":True,"response":response}

@app.post("/api/chat/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = UPLOADS / file.filename
    dest.write_bytes(await file.read())
    return {"path": str(dest), "name": file.filename}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await wsman.connect(ws)
    try:
        while True:
            await ws.send_json({"type":"ping","ts":datetime.now().isoformat()})
            await asyncio.sleep(30)
    except: wsman.disconnect(ws)

from starlette.responses import HTMLResponse as _HTMLResponse

@app.get("/api/health")
async def api_health(): return {"status":"ok"}

@app.get("/")
async def serve(): return _HTMLResponse(content=FRONTEND.read_text(), media_type="text/html; charset=utf-8")

@app.get("/dashboard")
async def serve_dashboard(): return _HTMLResponse(content=FRONTEND.read_text(), media_type="text/html; charset=utf-8")

@app.get("/dashboard/{path:path}")
async def serve_dashboard_path(path: str): return _HTMLResponse(content=FRONTEND.read_text(), media_type="text/html; charset=utf-8")

@app.get("/agents-room")
async def agents_room():
    p = PROJECT_ROOT / "dashboard" / "frontend" / "agents-room.html"
    return _HTMLResponse(content=p.read_text(), media_type="text/html; charset=utf-8")


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

@app.get("/api/agents")

@app.get("/api/agents")
async def get_agents(project_id: str = None, type: str = None, status: str = None, skill: str = None):
    async with pool.acquire() as c:
        q = """
            SELECT a.*,
                   kc.title AS current_task_title, kc.status AS current_task_status,
                   kc.priority AS current_task_priority, kc.project_id AS current_task_project_id,
                   kc.next_step AS current_task_next_step, kc.started_at AS current_task_started_at,
                   COALESCE((SELECT COUNT(*) FROM kanban_cards qk WHERE qk.assigned_agent_id=a.id AND qk.status IN ('planned','queue','idea')),0) AS queue_count
            FROM agents a
            LEFT JOIN kanban_cards kc ON kc.id=a.current_task_id
            WHERE 1=1
        """
        params = []
        if project_id:
            params.append(project_id); q += f" AND a.project_id=${len(params)}"
        if type:
            params.append(type); q += f" AND a.type=${len(params)}"
        if status:
            params.append(status); q += f" AND a.status=${len(params)}"
        if skill:
            params.append(skill); q += f" AND a.skills ? ${len(params)}"
        rows = await c.fetch(q + " ORDER BY CASE WHEN a.type LIKE 'general_agent%' THEN 0 ELSE 1 END, a.id", *params)
    return [_jsonable(r) for r in rows]

@app.get("/api/agents/general")
async def get_general_agents():
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT a.*, kc.title AS current_task_title, kc.status AS current_task_status,
                   kc.priority AS current_task_priority, kc.project_id AS current_task_project_id,
                   kc.next_step AS current_task_next_step, kc.started_at AS current_task_started_at,
                   kc.agent_discussion_id AS current_task_discussion_id,
                   COALESCE((SELECT COUNT(*) FROM kanban_cards qk WHERE qk.assigned_agent_id=a.id AND qk.status IN ('planned','queue','idea')),0) AS queue_count
            FROM agents a
            LEFT JOIN kanban_cards kc ON kc.id=a.current_task_id
            WHERE a.type LIKE 'general_agent%'
            ORDER BY CASE a.id WHEN 'pepe' THEN 1 WHEN 'anton' THEN 2 WHEN 'katya' THEN 3 ELSE 9 END
        """)
    return [_jsonable(r) for r in rows]

@app.get("/api/agents/counts")
async def agent_counts_for_ui():
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT COALESCE(project_id,'corp') AS project_id, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE status='active') as active
            FROM agents GROUP BY COALESCE(project_id,'corp')
        """)
    return {r['project_id']: {"total": int(r['total']), "active": int(r['active'])} for r in rows}

@app.get("/api/agents/stalls")
async def agent_stalls(threshold_minutes: int = 120, max_items: int = 50):
    safe_threshold = max(5, min(int(threshold_minutes or 120), 10080))
    safe_limit = max(1, min(int(max_items or 50), 200))
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT a.id AS agent_id, a.name, a.status, a.current_task_id, a.last_activity_at,
                   kc.title AS task_title, kc.priority, kc.project_id
            FROM agents a
            LEFT JOIN kanban_cards kc ON kc.id=a.current_task_id
            WHERE a.current_task_id IS NOT NULL
              AND a.status IN ('active','thinking')
              AND COALESCE(a.last_activity_at, a.active_since, NOW() - INTERVAL '100 years') < NOW() - ($1::text || ' minutes')::interval
            ORDER BY COALESCE(a.last_activity_at, a.active_since) ASC
            LIMIT $2
        """, str(safe_threshold), safe_limit)
    return {"threshold_minutes": safe_threshold, "max_items": safe_limit, "items": [_jsonable(r) for r in rows], "count": len(rows)}

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    async with pool.acquire() as c:
        a = await c.fetchrow("SELECT * FROM agents WHERE id=$1 OR slug=$1", agent_id)
        if not a: raise HTTPException(404, "agent not found")
        tasks = await c.fetch("SELECT * FROM kanban_cards WHERE assigned_agent_id=$1 OR agent_id=$1 ORDER BY moved_at DESC LIMIT 50", a['id'])
        activity = await c.fetch("SELECT * FROM agent_activity_log WHERE agent_id=$1 ORDER BY created_at DESC LIMIT 50", a['id'])
        chats = await c.fetch("SELECT * FROM agent_chats WHERE agent_id=$1 OR id='global-agents-chat' ORDER BY created_at", a['id'])
    return {"agent": _jsonable(a), "tasks": [_jsonable(r) for r in tasks], "activity": [_jsonable(r) for r in activity], "chats": [_jsonable(r) for r in chats]}

@app.get("/api/agent-chats/{chat_id}/messages")
async def get_agent_chat_messages(chat_id: str):
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM agent_messages WHERE chat_id=$1 ORDER BY created_at ASC LIMIT 300", chat_id)
    return [_jsonable(r) for r in rows]

class AgentMsgBody(BaseModel):
    text: str
    sender_type: str = "owner"
    sender_id: str = "owner"
    message_type: str = "owner_message"
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    parent_message_id: Optional[str] = None

@app.post("/api/agent-chats/{chat_id}/messages")
async def post_agent_chat_message(chat_id: str, body: AgentMsgBody):
    mid = "msg-" + str(uuid.uuid4())[:12]
    task_id = None
    project_id = None
    chat_title = chat_id
    agent_ids = []
    async with pool.acquire() as c:
        chat = await c.fetchrow("SELECT * FROM agent_chats WHERE id=$1", chat_id)
        if not chat: raise HTTPException(404, "chat not found")
        task_id = body.task_id or chat['task_id']
        project_id = body.project_id or chat['project_id'] or 'corp'
        chat_title = chat['title'] or chat_id
        await c.execute("""
            INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id,parent_message_id)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """, mid, chat_id, body.sender_type, body.sender_id, body.text, body.message_type, task_id, project_id, body.parent_message_id)
        if body.sender_type == 'owner' and chat['agent_id']:
            agent_ids = [chat['agent_id']]
            await c.execute("""
                INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                VALUES($1,$2,'message_sent',$3,$4,$5)
            """, "log-" + str(uuid.uuid4())[:12], chat['agent_id'], task_id, project_id, "Владелец написал агенту: " + body.text[:180])
        elif body.sender_type == 'owner' and chat['chat_type'] == 'global':
            agent_ids = ['pepe', 'anton', 'katya']
            for aid in agent_ids:
                await c.execute("""
                    INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                    VALUES($1,$2,'message_received',$3,$4,$5)
                """, "log-" + str(uuid.uuid4())[:12], aid, task_id, project_id, "Владелец написал в общий чат: " + body.text[:180])
        await c.execute("UPDATE agent_chats SET updated_at=NOW() WHERE id=$1", chat_id)

    reply_ids = []
    if body.sender_type == 'owner' and agent_ids:
        for aid in agent_ids:
            reply_text = await _agent_reply(aid, body.text, chat_title, task_id, project_id)
            message_type = 'agent_to_agent' if chat_id == 'global-agents-chat' and aid != 'pepe' else 'agent_message'
            async with pool.acquire() as c:
                rid = await _insert_agent_message(c, chat_id, aid, reply_text, message_type, task_id, project_id)
                reply_ids.append(rid)
                if chat_id == 'global-agents-chat' and aid == 'pepe':
                    await c.execute("""
                        INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id,parent_message_id)
                        VALUES($1,$2,'system','system',$3,'system_event',$4,$5,$6)
                    """, "msg-" + str(uuid.uuid4())[:12], chat_id, "Система передала сообщение Пепе, Антону и Кате. Ответы сохранены в общий чат и журнал активности.", task_id, project_id, rid)
                await c.execute("UPDATE agent_chats SET updated_at=NOW() WHERE id=$1", chat_id)
    return {"ok": True, "id": mid, "reply_ids": reply_ids, "agents_notified": agent_ids}

class TaskFromMessageBody(BaseModel):
    title: str
    description: str = ""
    message_id: Optional[str] = None
    agent_id: Optional[str] = None
    curator_agent_id: Optional[str] = "pepe"
    project_id: Optional[str] = "corp"
    priority: str = "P2"
    required_skills: List[str] = []

@app.post("/api/agent-chats/{chat_id}/create-task")
async def create_task_from_agent_chat(chat_id: str, body: TaskFromMessageBody):
    cid = "task-" + str(uuid.uuid4())[:10]
    async with pool.acquire() as c:
        chat = await c.fetchrow("SELECT * FROM agent_chats WHERE id=$1", chat_id)
        if not chat: raise HTTPException(404, "chat not found")
        source_msg = None
        if body.message_id:
            source_msg = await c.fetchrow("SELECT * FROM agent_messages WHERE id=$1 AND chat_id=$2", body.message_id, chat_id)
        if source_msg is None:
            source_msg = await c.fetchrow("SELECT * FROM agent_messages WHERE chat_id=$1 ORDER BY created_at DESC LIMIT 1", chat_id)
        assigned_agent_id = body.agent_id or chat['agent_id']
        project_id = body.project_id or chat['project_id'] or (source_msg['project_id'] if source_msg else None) or 'corp'
        description = body.description or (source_msg['text'] if source_msg else '') or 'Создано из чата агентов'
        await c.execute("""
            INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,assigned_agent_id,curator_agent_id,required_skills,agent_discussion_id,next_step)
            VALUES($1,$2,$3,'task','operational',$4,$5::text,'queue',$6,ARRAY['agent-chat'],$5::text,$7,$8::jsonb,$9,'Уточнить первый исполнимый шаг')
        """, cid, body.title, description, project_id, assigned_agent_id, body.priority, body.curator_agent_id, json.dumps(body.required_skills or []), chat_id)
        if source_msg:
            await c.execute("""
                UPDATE agent_messages
                SET task_id=$1, project_id=$2, message_type=CASE WHEN message_type='owner_message' THEN 'task_update' ELSE message_type END
                WHERE id=$3
            """, cid, project_id, source_msg['id'])
        system_message_id = "msg-" + str(uuid.uuid4())[:12]
        await c.execute("""
            INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id,parent_message_id)
            VALUES($1,$2,'system','system',$3,'task_update',$4,$5,$6)
        """, system_message_id, chat_id, f"Создана задача канбана: {body.title}", cid, project_id, source_msg['id'] if source_msg else None)
        if assigned_agent_id:
            await c.execute("INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text) VALUES($1,$2,'task_created',$3,$4,$5)", "log-" + str(uuid.uuid4())[:12], assigned_agent_id, cid, project_id, "Создана задача из сообщения чата: " + body.title)
            await c.execute("INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text) VALUES($1,$2,'task_assigned',$3,$4,$5)", "log-" + str(uuid.uuid4())[:12], assigned_agent_id, cid, project_id, "Задача назначена агенту из чата: " + body.title)
            await c.execute("""
                UPDATE agents
                SET current_task_id=$1,
                    status=CASE WHEN status='paused' THEN 'paused' ELSE 'active' END,
                    active_since=NOW(),
                    last_activity_at=NOW(), updated_at=NOW()
                WHERE id=$2
            """, cid, assigned_agent_id)
    return {"ok": True, "id": cid, "source_message_id": source_msg['id'] if source_msg else None, "assigned_agent_id": assigned_agent_id, "reply_ids": [system_message_id]}

@app.get("/api/agent-activity")
async def get_agent_activity(agent_id: str = None, task_id: str = None):
    async with pool.acquire() as c:
        q = "SELECT * FROM agent_activity_log WHERE 1=1"; params=[]
        if agent_id:
            params.append(agent_id); q += f" AND agent_id=${len(params)}"
        if task_id:
            params.append(task_id); q += f" AND task_id=${len(params)}"
        rows = await c.fetch(q + " ORDER BY created_at DESC LIMIT 100", *params)
    return [_jsonable(r) for r in rows]


@app.get("/api/board/messages")
async def board_messages():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    streams = ['corp:tasks','corp:results','corp:alerts','corp:costs','corp:health','corp:parallel_events','corp:kanban_events']
    messages = []
    try:
        for stream in streams:
            try:
                entries = await r.xrevrange(stream, count=30)
                for eid, data in entries:
                    ts = float(eid.split('-')[0]) / 1000
                    messages.append({
                        "id": eid, "stream": stream.split(':')[1],
                        "data": data, "ts": ts,
                        "time": datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                    })
            except: pass
    finally:
        await r.aclose()
    messages.sort(key=lambda x: x['ts'], reverse=True)
    return messages[:100]

class BoardMsg(BaseModel):
    content: str
    target: str = "corp"

class InboxRouteBody(BaseModel):
    message: str
    source: str = "dashboard"
    owner_id: str = "owner"

@app.post("/api/inbox/route")
async def inbox_route(body: InboxRouteBody):
    if is_project_company_request(body.message):
        return await route_project_company(pool, REDIS_URL, body.message, source=body.source)
    return {"ok": False, "intent_class": "UNKNOWN", "status": "not_handled", "response": "Master Router не распознал запрос как PROJECT_COMPANY_REQUEST."}

@app.get("/api/project-companies/{pid}/workroom")
async def project_workroom(pid: str, kind: str = "chat"):
    content = read_workroom(pid, kind) or ""
    return {"project_id": pid.lower(), "kind": kind, "content": content}

@app.post("/api/board/send")
async def board_send(body: BoardMsg):
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    stream = f"{body.target}:tasks" if body.target != "corp" else "corp:tasks"
    agents = ['pepe', 'anton', 'katya'] if body.target == 'corp' else ['pepe']
    reply_ids = []
    try:
        await r.xadd(stream, {
            "source": "dashboard",
            "agent": "owner",
            "message": body.content,
            "ts": str(datetime.now().timestamp())
        })
        async with pool.acquire() as c:
            owner_mid = "msg-" + str(uuid.uuid4())[:12]
            await c.execute("""
                INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,project_id)
                VALUES($1,'global-agents-chat','owner','owner',$2,'owner_message',$3)
            """, owner_mid, body.content, body.target)
        for aid in agents:
            reply_text = _fallback_agent_reply(aid, body.content)
            await r.xadd('corp:results', {
                "source": "dashboard",
                "agent": aid,
                "message": reply_text,
                "target": body.target,
                "ts": str(datetime.now().timestamp())
            })
            async with pool.acquire() as c:
                rid = await _insert_agent_message(c, 'global-agents-chat', aid, reply_text, 'agent_to_agent' if aid != 'pepe' else 'agent_message', None, body.target)
                reply_ids.append(rid)
    finally:
        await r.aclose()
    return {"ok": True, "stream": stream, "agents_notified": agents, "reply_ids": reply_ids}

@app.post("/api/agents/{agent_id}/ping")
async def ping_agent(agent_id: str):
    async with pool.acquire() as c:
        await c.execute("UPDATE agents SET last_heartbeat=NOW(), status='active' WHERE id=$1", agent_id)
    return {"ok": True}

@app.get("/api/agent-events/recent")
async def agent_events_recent(limit: int = 50):
    lim = max(1, min(limit, 200))
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM agent_events ORDER BY created_at DESC LIMIT $1", lim)
    return {"success": True, "items": [_jsonable(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

@app.get("/api/agent-events/by-task/{task_id}")
async def agent_events_by_task(task_id: str):
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM agent_events WHERE task_id=$1 ORDER BY created_at ASC", task_id)
    return {"success": True, "items": [_jsonable(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

@app.get("/api/agents/activity")
async def agents_activity():
    sql = """
    WITH t AS (
      SELECT
        COALESCE(to_agent, from_agent) AS agent,
        task_id,
        status,
        event_type,
        message,
        skills_used,
        created_at,
        ROW_NUMBER() OVER (
          PARTITION BY COALESCE(to_agent, from_agent)
          ORDER BY created_at DESC
        ) AS rn
      FROM agent_events
      WHERE COALESCE(to_agent, from_agent) IS NOT NULL
    )
    SELECT
      agent,
      status AS current_status,
      task_id AS current_task,
      event_type AS last_event_type,
      message AS last_message,
      created_at AS last_seen_at,
      skills_used
    FROM t
    WHERE rn = 1
    ORDER BY last_seen_at DESC
    """
    async with pool.acquire() as c:
        rows = await c.fetch(sql)
    return {"success": True, "items": [_jsonable(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

