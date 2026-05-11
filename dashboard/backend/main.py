from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from collections import defaultdict
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import asyncpg, psutil, subprocess, asyncio, os, uuid, json, httpx, redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv("/Users/admin/workspace/digital-corp/core/.env")
DB = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"
FRONTEND = Path("/Users/admin/workspace/digital-corp/dashboard/frontend/index.html")
UPLOADS = Path("/Users/admin/workspace/digital-corp/dashboard/uploads")
UPLOADS.mkdir(exist_ok=True)
pool = None

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
    pool = await asyncpg.create_pool(DB, min_size=2, max_size=10)
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
        services = {'hermes': 'hermes' in lctl.stdout, 'a01': 'a01' in lctl.stdout}
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
    log_path = Path(f"/Users/admin/workspace/digital-corp/logs/{pid}.log")
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
        "/Users/admin/workspace/digital-corp/agents/a06-research/research_agent.py",
    ], stdout=open("/Users/admin/workspace/digital-corp/logs/a06.log", "a"), stderr=subprocess.STDOUT)
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

@app.get("/api/kanban")
async def get_kanban(layer: str = "strategic", project_id: str = None, card_type: str = None):
    async with pool.acquire() as c:
        q = "SELECT * FROM kanban_cards WHERE layer=$1"
        params = [layer]
        if project_id:
            q += f" AND project_id=${len(params)+1}"
            params.append(project_id)
        if card_type:
            q += f" AND card_type=${len(params)+1}"
            params.append(card_type)
        rows = await c.fetch(q + " ORDER BY priority, moved_at ASC", *params)
    cards = []
    now = datetime.now().astimezone()
    for r in rows:
        d = dict(r)
        moved_at = d.get('moved_at')
        if moved_at:
            delta = now - moved_at
            hrs = int(delta.total_seconds() // 3600)
            d['time_in_stage_hrs'] = hrs
            d['time_in_stage'] = f"{hrs}ч" if hrs < 48 else f"{hrs//24}д"
        else:
            d['time_in_stage_hrs'] = 0
            d['time_in_stage'] = '—'
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
        await c.execute("UPDATE kanban_cards SET status=$1, moved_at=NOW(), updated_at=NOW() WHERE id=$2", body.status, card_id)
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

async def call_hermes(message: str, session_id: str) -> str:
    # Try HTTP API first (if Hermes gateway exposes one)
    hermes_port = os.getenv("HERMES_PORT", "8000")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for path in ["/api/chat", "/chat", "/v1/chat/completions"]:
                try:
                    r = await client.post(f"http://localhost:{hermes_port}{path}",
                                          json={"message": message, "session_id": session_id})
                    if r.status_code == 200:
                        d = r.json()
                        return d.get("response") or d.get("content") or d.get("choices", [{}])[0].get("message", {}).get("content", str(d))
                except: continue
    except: pass
    # Try Hermes CLI
    try:
        r = subprocess.run(
            ["hermes", "chat", "-q", message],
            capture_output=True, text=True, timeout=90,
            env={**os.environ, "PATH": "/Users/admin/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
        )
        if r.returncode == 0:
            out = (r.stdout or "").strip()
            if out:
                lines = [ln.rstrip() for ln in out.splitlines()]
                cleaned = []
                for ln in lines:
                    if ln.startswith(("Query:", "Initializing agent", "Resume this session with:", "Session:", "Duration:", "Messages:")):
                        continue
                    if ln.strip() in {"────────────────────────────────────────", "╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮", "╰──────────────────────────────────────────────────────────────────────────────╯"}:
                        continue
                    cleaned.append(ln)
                cleaned = "\n".join([ln for ln in cleaned if ln.strip()])
                return cleaned[:2000] if cleaned else out[:2000]
    except Exception:
        pass
    return "⚠️ Hermes не подключён. Попробуй: hermes chat -q 'твой вопрос' в терминале."

@app.post("/api/chat/send")
async def send_msg(body: MsgBody):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO chat_messages(session_id,role,content) VALUES($1,'user',$2)", body.session_id, body.content)
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
@app.get("/")
async def serve(): return _HTMLResponse(content=FRONTEND.read_text(), media_type="text/html; charset=utf-8")

@app.get("/agents-room")
async def agents_room():
    p = Path("/Users/admin/workspace/digital-corp/dashboard/frontend/agents-room.html")
    return _HTMLResponse(content=p.read_text(), media_type="text/html; charset=utf-8")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

@app.get("/api/agents")
async def get_agents(project_id: str = None):
    async with pool.acquire() as c:
        if project_id:
            rows = await c.fetch("SELECT * FROM agents WHERE project_id=$1 ORDER BY id", project_id)
        else:
            rows = await c.fetch("SELECT * FROM agents ORDER BY project_id, id")
    return [dict(r) for r in rows]

@app.get("/api/agents/counts")
async def agent_counts():
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT project_id, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE status='active') as active
            FROM agents GROUP BY project_id
        """)
    return {r['project_id']: {"total": int(r['total']), "active": int(r['active'])} for r in rows}

@app.get("/api/board/messages")
async def board_messages():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    streams = ['corp:tasks','corp:results','corp:alerts','corp:costs','corp:health']
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

class InboxEventBody(BaseModel):
    raw_text: str
    source: str = "dashboard"
    source_message_id: Optional[str] = None
    owner_id: Optional[str] = None
    normalized_intent: Optional[str] = None
    intent_class: str = "UNKNOWN"
    project_id: Optional[str] = None
    priority: str = "P2"
    risk_level: str = "low"
    status: str = "received"
    requires_approval: bool = False
    approval_id: Optional[str] = None
    agents_used: List[str] = []
    skills_used: List[str] = []
    cost_usd: float = 0.0
    result_summary: Optional[str] = None
    error_summary: Optional[str] = None
    metadata: dict = {}

class InboxRouteBody(BaseModel):
    message: str
    source: str = "dashboard"
    owner_id: Optional[str] = None

RISK_WORDS = ("удали", "delete", "drop", "truncate", "внешний доступ", "деплой", "deploy", ".env", "секрет", "ключ")

def normalize_priority(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("срочно", "немедленно", "критично", "p0")):
        return "P0"
    if any(w in t for w in ("важно", "p1")):
        return "P1"
    if any(w in t for w in ("потом", "низкий", "p3")):
        return "P3"
    return "P2"

def normalize_status(text: str) -> Optional[str]:
    t = text.lower()
    if any(w in t for w in ("готово", "done", "заверш", "закры")):
        return "done"
    if any(w in t for w in ("в работу", "работе", "in_progress", "делать")):
        return "in_progress"
    if any(w in t for w in ("замороз", "frozen")):
        return "frozen"
    if any(w in t for w in ("блок", "blocked")):
        return "blocked"
    if any(w in t for w in ("план", "planned")):
        return "planned"
    return None

def classify_owner_message(text: str) -> dict:
    t = (text or "").strip().lower()
    priority = normalize_priority(t)
    if not t:
        return {"intent_class": "UNKNOWN", "priority": priority, "risk_level": "low", "requires_approval": False}
    risky = any(w in t for w in RISK_WORDS)
    if t.startswith(("/с", "/статус")) or "статус" in t or "что с системой" in t:
        intent = "SYSTEM_STATUS"
    elif " и " in t and any(w in t for w in ("расход", "завис", "статус", "канбан")):
        intent = "COMPLEX"
    elif t.startswith(("/б", "/бюджет")) or "расход" in t or "бюджет" in t or "потрати" in t:
        intent = "COST_QUERY"
    elif t.startswith(("/к", "/канбан")) or "канбан" in t or "что в работе" in t or "завис" in t:
        intent = "KANBAN_VIEW"
    elif t.startswith("/п ") or t.startswith("/поставь ") or "добавь задачу" in t or "поставь задачу" in t:
        intent = "KANBAN_CREATE"
    elif "перемести" in t or "поставь в работу" in t or "в готово" in t or "заморозь" in t:
        intent = "KANBAN_MOVE"
    elif t.startswith(("/г", "/гит")) or "что в гите" in t or "git" in t or "гит" in t:
        intent = "GIT_STATUS"
    elif t.startswith(("/з", "/знания")) or "знани" in t or "устарел" in t:
        intent = "KNOWLEDGE_CHECK"
    elif t.startswith("/инбокс"):
        intent = "INBOX_VIEW"
    elif t.startswith("/алерты"):
        intent = "ALERTS_VIEW"
    elif t.startswith("/долги"):
        intent = "DEBTS_VIEW"
    elif t in {"/д", "/день"} or t.startswith("/день ") or "бриф" in t:
        intent = "MORNING_BRIEF_NOW"
    elif t.startswith("/риск") or "это опасно" in t or "проверь риск" in t:
        intent = "RISK_REVIEW"
    elif risky:
        intent = "RISK_REVIEW"
    elif " и " in t and any(w in t for w in ("расход", "завис", "статус", "канбан")):
        intent = "COMPLEX"
    else:
        intent = "UNKNOWN"
    risk_level = "high" if risky else "low"
    return {"intent_class": intent, "priority": priority, "risk_level": risk_level, "requires_approval": risky}

def extract_task_title(text: str) -> str:
    raw = (text or "").strip()
    lowered = raw.lower()
    prefixes = ["/п ", "добавь задачу", "поставь задачу", "поставь "]
    for pref in prefixes:
        if lowered.startswith(pref):
            return raw[len(pref):].strip(" :-") or raw
    return raw

def extract_move_query(text: str) -> str:
    raw = (text or "").strip()
    t = raw.lower()
    for token in ("перемести", "поставь"):
        if t.startswith(token):
            raw = raw[len(token):].strip(" :-")
            t = raw.lower()
    for sep in (" в готово", " в работу", " в done", " в in_progress", " в план", " в planned"):
        idx = t.find(sep)
        if idx > 0:
            return raw[:idx].strip(" :-")
    return raw[:120]

async def insert_inbox_event_record(body: InboxEventBody, status: Optional[str] = None) -> tuple[str, Optional[str]]:
    event_id = f"inbox_{uuid.uuid4().hex[:12]}"
    if body.requires_approval and not body.approval_id:
        body.approval_id = f"appr_{uuid.uuid4().hex[:10]}"
    final_status = status or body.status
    async with pool.acquire() as c:
        await c.execute("""
            INSERT INTO inbox_events
            (event_id, source, source_message_id, owner_id, raw_text, normalized_intent, intent_class,
             project_id, priority, risk_level, status, requires_approval, approval_id, agents_used,
             skills_used, cost_usd, result_summary, error_summary, metadata, completed_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15::jsonb,$16,$17,$18,$19::jsonb,$20)
        """, event_id, body.source, body.source_message_id, body.owner_id, body.raw_text, body.normalized_intent,
             body.intent_class, body.project_id, body.priority, body.risk_level, final_status, body.requires_approval,
             body.approval_id, json.dumps(body.agents_used, ensure_ascii=False), json.dumps(body.skills_used, ensure_ascii=False),
             body.cost_usd, body.result_summary, body.error_summary, json.dumps(body.metadata, ensure_ascii=False, default=str),
             datetime.now() if final_status == "completed" else None)
    return event_id, body.approval_id

async def write_redis_event(stream: str, payload: dict):
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        return await r.xadd(stream, {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, bool)) else "" if v is None else str(v) for k, v in payload.items()})
    finally:
        await r.aclose()

@app.post("/api/inbox/events")
async def create_inbox_event(body: InboxEventBody):
    event_id, approval_id = await insert_inbox_event_record(body)
    redis_payload = {
        "event_id": event_id,
        "source": body.source,
        "source_message_id": body.source_message_id,
        "owner_id": body.owner_id,
        "project_id": body.project_id,
        "intent": body.intent_class,
        "message": body.raw_text,
        "priority": body.priority,
        "risk_level": body.risk_level,
        "requires_approval": body.requires_approval,
        "approval_id": approval_id,
        "created_at": datetime.now().isoformat(),
    }
    stream_id = await write_redis_event("corp:inbox", redis_payload)
    if body.requires_approval:
        await write_redis_event("corp:approvals", redis_payload)
    if body.risk_level in {"medium", "high", "critical"} or body.requires_approval:
        await write_redis_event("corp:audit", {
            "audit_id": f"audit_{uuid.uuid4().hex[:12]}",
            "actor": body.source,
            "action": body.intent_class,
            "target": body.project_id or "corp",
            "risk_level": body.risk_level,
            "before_summary": "inbox event received",
            "after_summary": body.result_summary or "waiting route/approval",
            "created_at": datetime.now().isoformat(),
            "event_id": event_id,
        })
    await wsman.broadcast({"type": "inbox_event", "event_id": event_id, "intent_class": body.intent_class, "status": body.status})
    return {"ok": True, "event_id": event_id, "stream": "corp:inbox", "stream_id": stream_id, "approval_id": approval_id}

async def build_morning_brief() -> tuple[str, dict]:
    sys = await system_metrics()
    costs = await costs_today()
    async with pool.acquire() as c:
        active = await c.fetchval("SELECT COUNT(*) FROM projects WHERE status='active'")
        agents = await c.fetchval("SELECT COUNT(*) FROM agents")
        work = await c.fetch("""
            SELECT title,priority,status FROM kanban_cards
            WHERE status IN ('in_progress','blocked')
            ORDER BY priority,moved_at ASC LIMIT 3
        """)
        blocked = await c.fetch("""
            SELECT title,priority,status FROM kanban_cards
            WHERE status IN ('blocked','frozen')
            ORDER BY priority,moved_at ASC LIMIT 3
        """)
    work_bullets = "\n".join([f"• [{r['priority']}] {r['title']} — {r['status']}" for r in work]) or "• критичных пунктов нет"
    blocked_bullets = "\n".join([f"• [{r['priority']}] {r['title']} — {r['status']}" for r in blocked]) or "• нет"
    text = (
        f"🏛 Доброе утро. Корпорация.\n"
        f"СИСТЕМА:\n"
        f"• CPU {sys['cpu']}%, RAM {sys['ram_pct']}%\n"
        f"• Расходы 24ч: ${costs['total']:.6f}\n"
        f"• Активные проекты: {active}; агенты: {agents}\n"
        f"В РАБОТЕ:\n{work_bullets}\n"
        f"ЗАБЛОКИРОВАНО:\n{blocked_bullets}"
    )
    return text, {"system": sys, "costs": costs, "active_projects": active, "agents": agents, "blocked_count": len(blocked), "work_count": len(work)}

@app.get("/api/inbox/morning-brief")
async def inbox_morning_brief():
    text, data = await build_morning_brief()
    return {"ok": True, "brief": text, "data": data, "ts": datetime.now().isoformat()}

@app.post("/api/inbox/route")
async def route_inbox_message(body: InboxRouteBody):
    message = body.message.strip()
    cls = classify_owner_message(message)
    intent = cls["intent_class"]
    priority = cls["priority"]
    risk_level = cls["risk_level"]
    requires_approval = cls["requires_approval"]
    response = ""
    data = {}
    status = "completed"
    skills_used = ["master-router"]

    if requires_approval:
        response = "Нужно подтверждение.\nХочу: выполнить рискованное действие из сообщения.\nРиск: возможны данные/секреты/внешний доступ.\nЦена: н/д.\nОткат: зависит от действия.\nA — да, делай\nB — нет, отмени\nC — безопасный вариант"
        status = "waiting_approval"
    elif intent == "SYSTEM_STATUS":
        sys = await system_metrics()
        db_ok = True
        data = {"system": sys}
        response = f"Готово: система отвечает, CPU {sys['cpu']}%, RAM {sys['ram_pct']}%.\nДальше: ничего не нужно."
    elif intent == "COST_QUERY":
        costs = await costs_today()
        data = costs
        response = f"Готово: расходы за 24ч ${costs['total']:.6f}.\nДальше: ничего не нужно."
    elif intent == "KANBAN_VIEW":
        async with pool.acquire() as c:
            rows = await c.fetch("""
                SELECT id,title,status,priority,project_id,layer,moved_at
                FROM kanban_cards
                WHERE status IN ('in_progress','blocked','frozen')
                ORDER BY priority, moved_at ASC LIMIT 12
            """)
        items = [dict(r) for r in rows]
        data = {"items": items}
        if items:
            compact = "; ".join([f"[{i['priority']}] {i['title']} — {i['status']}" for i in items[:5]])
            response = f"Готово: в фокусе {len(items)} задач. {compact}."
        else:
            response = "Готово: активных/заблокированных задач не найдено.\nДальше: можно поставить задачу через /п текст."
        skills_used.append("kanban-aggregator")
    elif intent == "KANBAN_CREATE":
        title = extract_task_title(message)[:200]
        cid = f"inbox-{uuid.uuid4().hex[:10]}"
        layer = "strategic" if any(w in message.lower() for w in ("стратег", "цель", "видение")) else "operational"
        async with pool.acquire() as c:
            await c.execute("""
                INSERT INTO kanban_cards (id,title,description,card_type,layer,project_id,status,priority,tags,metadata)
                VALUES ($1,$2,$3,'task',$4,NULL,'planned',$5,$6,$7::jsonb)
            """, cid, title, "Created by inbox master-router", layer, priority, ["inbox"], json.dumps({"source": body.source}, ensure_ascii=False))
        data = {"card_id": cid, "title": title, "priority": priority, "layer": layer}
        response = f"Готово: добавил задачу [{priority}] {title}.\nДальше: ничего не нужно."
        skills_used.append("kanban-aggregator")
    elif intent == "KANBAN_MOVE":
        target_status = normalize_status(message) or "done"
        query = extract_move_query(message)
        async with pool.acquire() as c:
            candidates = await c.fetch("""
                SELECT id,title,status,priority FROM kanban_cards
                WHERE lower(title) LIKE lower($1)
                ORDER BY moved_at DESC LIMIT 5
            """, f"%{query}%")
            if len(candidates) == 1:
                row = candidates[0]
                await c.execute("UPDATE kanban_cards SET status=$1, moved_at=NOW(), updated_at=NOW() WHERE id=$2", target_status, row['id'])
                data = {"card_id": row['id'], "title": row['title'], "status": target_status}
                response = f"Готово: {row['title']} → {target_status}.\nДальше: ничего не нужно."
            elif len(candidates) == 0:
                response = f"Не нашёл карточку: {query}.\nДальше: уточни название."
            else:
                status = "waiting_approval"
                options = "\n".join([f"{idx+1} — {r['title']} ({r['status']})" for idx, r in enumerate(candidates[:3])])
                response = f"Нужно уточнение.\n{options}"
                data = {"candidates": [dict(r) for r in candidates]}
        skills_used.append("kanban-aggregator")
    elif intent == "GIT_STATUS":
        proc = await asyncio.create_subprocess_exec('git','status','--short', cwd='/Users/admin/workspace/digital-corp', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate()
        proc2 = await asyncio.create_subprocess_exec('git','log','--oneline','-5', cwd='/Users/admin/workspace/digital-corp', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        log, _ = await proc2.communicate()
        changes = (out.decode().strip() or "чисто")
        data = {"status": changes, "log": log.decode().strip()}
        response = f"Готово: git status — {changes.splitlines()[0] if changes else 'чисто'}.\nДальше: ничего не нужно."
    elif intent == "KNOWLEDGE_CHECK":
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT name,status,freshness_score FROM knowledge_items WHERE status <> 'ok' ORDER BY freshness_score ASC NULLS FIRST LIMIT 5")
        data = {"items": [dict(r) for r in rows]}
        response = f"Готово: найдено {len(rows)} проблемных knowledge items.\nДальше: /з для деталей."
    elif intent == "MORNING_BRIEF_NOW":
        response, data = await build_morning_brief()
        skills_used.append("morning-brief")
    elif intent == "INBOX_VIEW":
        recent = await inbox_events_recent(10)
        data = recent
        response = f"Готово: последних inbox events — {recent['count']}.\nДальше: ничего не нужно."
    elif intent == "ALERTS_VIEW":
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        try:
            alerts = await r.xrevrange('corp:alerts', count=5)
        finally:
            await r.aclose()
        data = {"alerts": alerts}
        response = f"Готово: последних алертов — {len(alerts)}.\nДальше: ничего не нужно."
    elif intent == "DEBTS_VIEW":
        async with pool.acquire() as c:
            rows = await c.fetch("""
                SELECT id,title,status,priority,moved_at FROM kanban_cards
                WHERE (status='in_progress' AND moved_at < NOW()-INTERVAL '3 days')
                   OR (status IN ('blocked','frozen') AND moved_at < NOW()-INTERVAL '7 days')
                ORDER BY priority,moved_at ASC LIMIT 10
            """)
        data = {"items": [dict(r) for r in rows]}
        response = f"Готово: найдено зависших задач — {len(rows)}.\nДальше: разберу P0/P1 по запросу."
        skills_used.append("kanban-aggregator")
    elif intent == "RISK_REVIEW":
        response = "Готово: риск высокий, действие не выполняю автоматически.\nДальше: могу предложить безопасный вариант через подтверждение A/B/C."
    elif intent == "COMPLEX":
        costs = await costs_today()
        async with pool.acquire() as c:
            stuck = await c.fetchval("SELECT COUNT(*) FROM kanban_cards WHERE status IN ('blocked','frozen')")
        data = {"costs": costs, "blocked_or_frozen": stuck}
        response = f"Готово: расходы 24ч ${costs['total']:.6f}; blocked/frozen задач {stuck}.\nДальше: могу разобрать одну проблему."
    else:
        status = "classified"
        response = "Нужно уточнение.\nA — поставить задачу в канбан\nB — проверить статус/расходы\nC — оценить риск"

    event_body = InboxEventBody(
        raw_text=message, source=body.source, owner_id=body.owner_id, normalized_intent=message.lower(),
        intent_class=intent, priority=priority, risk_level=risk_level, status=status, requires_approval=requires_approval,
        skills_used=skills_used, result_summary=response[:500], metadata={"route_data": data}
    )
    event_id, approval_id = await insert_inbox_event_record(event_body, status=status)
    redis_payload = {"event_id": event_id, "source": body.source, "owner_id": body.owner_id, "intent": intent, "message": message, "priority": priority, "risk_level": risk_level, "requires_approval": requires_approval, "approval_id": approval_id, "created_at": datetime.now().isoformat()}
    await write_redis_event("corp:inbox", redis_payload)
    if requires_approval or status == "waiting_approval":
        await write_redis_event("corp:approvals", redis_payload)
    if requires_approval or risk_level in {"medium", "high", "critical"}:
        await write_redis_event("corp:audit", {"audit_id": f"audit_{uuid.uuid4().hex[:12]}", "actor": body.source, "action": intent, "target": "corp", "risk_level": risk_level, "after_summary": response[:300], "created_at": datetime.now().isoformat(), "event_id": event_id})
    await wsman.broadcast({"type":"inbox_route", "event_id": event_id, "intent_class": intent, "status": status})
    return {"ok": True, "event_id": event_id, "approval_id": approval_id, "intent_class": intent, "status": status, "response": response, "data": data}

@app.get("/api/inbox/events/recent")
async def inbox_events_recent(limit: int = 20):
    lim = max(1, min(limit, 100))
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM inbox_events ORDER BY created_at DESC LIMIT $1", lim)
    return {"success": True, "items": [dict(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

@app.get("/api/approvals/pending")
async def pending_approvals(limit: int = 20):
    lim = max(1, min(limit, 100))
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT * FROM inbox_events
            WHERE requires_approval = TRUE AND status IN ('received','classified','waiting_approval')
            ORDER BY created_at DESC LIMIT $1
        """, lim)
    return {"success": True, "items": [dict(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

@app.post("/api/board/send")
async def board_send(body: BoardMsg):
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    stream = f"{body.target}:tasks" if body.target != "corp" else "corp:tasks"
    try:
        await r.xadd(stream, {
            "source": "dashboard",
            "agent": "owner",
            "message": body.content,
            "task_id": task_id,
            "event_id": event_id,
            "ts": str(datetime.now().timestamp())
        })
    finally:
        await r.aclose()

    async with pool.acquire() as c:
        await c.execute("""
            INSERT INTO agent_events
            (event_id, project_id, task_id, from_agent, to_agent, event_type, status, priority, message, skills_used, tools_used, cost_usd, metadata)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'[]'::jsonb,'[]'::jsonb,$10,$11::jsonb)
        """, event_id, 'corp', task_id, 'owner', body.target, 'delegated', 'queued', 'P2', body.content, 0.0, '{}')

    return {"ok": True, "stream": stream, "event_id": event_id, "task_id": task_id}

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
    return {"success": True, "items": [dict(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

@app.get("/api/agent-events/by-task/{task_id}")
async def agent_events_by_task(task_id: str):
    async with pool.acquire() as c:
        rows = await c.fetch("SELECT * FROM agent_events WHERE task_id=$1 ORDER BY created_at ASC", task_id)
    return {"success": True, "items": [dict(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}

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
    return {"success": True, "items": [dict(r) for r in rows], "count": len(rows), "ts": datetime.now().isoformat()}
