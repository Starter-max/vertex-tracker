from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from collections import defaultdict
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import asyncpg, psutil, subprocess, asyncio, os, uuid, json, httpx, redis.asyncio as aioredis
from dotenv import load_dotenv
from company_builder import is_project_company_request, route_project_company, read_workroom

load_dotenv("/Volumes/256/digital-corp/core/.env", override=True)
DB = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": "localhost",
    "port": 5432,
}
FRONTEND = Path("/Volumes/256/digital-corp/dashboard/frontend/index.html")
UPLOADS = Path("/Volumes/256/digital-corp/dashboard/uploads")
UPLOADS.mkdir(exist_ok=True)
pool = None

async def apply_general_agents_migration():
    path = Path("/Volumes/256/digital-corp/core/migrations/007_general_agents.sql")
    if path.exists():
        async with pool.acquire() as c:
            await c.execute(path.read_text())

def _jsonable(row):
    d = dict(row)
    json_fields = {
        'mandate', 'restrictions', 'skills', 'metadata', 'required_skills',
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
    log_path = Path(f"/Volumes/256/digital-corp/logs/{pid}.log")
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
        "/Volumes/256/digital-corp/agents/a06-research/research_agent.py",
    ], stdout=open("/Volumes/256/digital-corp/logs/a06.log", "a"), stderr=subprocess.STDOUT)
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
    roots = [Path("/Users/admin/.hermes/skills"), Path("/Volumes/256/digital-corp/skills")]
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
    for root in [Path("/Users/admin/.hermes/skills"), Path("/Volumes/256/digital-corp/skills")]:
        if not root.exists():
            continue
        for md in root.rglob("SKILL.md"):
            item = _skill_summary_from_path(md)
            if item["name"] == safe or md.parent.name == safe:
                return {**item, "content": md.read_text(errors="ignore")[:20000]}
    raise HTTPException(404, "skill not found")

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
@app.get("/")
async def serve(): return _HTMLResponse(content=FRONTEND.read_text(), media_type="text/html; charset=utf-8")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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

@app.post("/api/agent-chats/{chat_id}/messages")
async def post_agent_chat_message(chat_id: str, body: AgentMsgBody):
    mid = "msg-" + str(uuid.uuid4())[:12]
    async with pool.acquire() as c:
        chat = await c.fetchrow("SELECT * FROM agent_chats WHERE id=$1", chat_id)
        if not chat: raise HTTPException(404, "chat not found")
        await c.execute("""
            INSERT INTO agent_messages(id,chat_id,sender_type,sender_id,text,message_type,task_id,project_id)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8)
        """, mid, chat_id, body.sender_type, body.sender_id, body.text, body.message_type, body.task_id or chat['task_id'], body.project_id or chat['project_id'])
        if body.sender_type == 'owner' and chat['agent_id']:
            await c.execute("""
                INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                VALUES($1,$2,'message_sent',$3,$4,$5)
            """, "log-" + str(uuid.uuid4())[:12], chat['agent_id'], body.task_id or chat['task_id'], body.project_id or chat['project_id'], "Владелец написал агенту: " + body.text[:180])
    return {"ok": True, "id": mid}

class TaskFromMessageBody(BaseModel):
    title: str
    description: str = ""
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
        await c.execute("""
            INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,assigned_agent_id,curator_agent_id,required_skills,agent_discussion_id,next_step)
            VALUES($1,$2,$3,'task','operational',$4,$5,'queue',$6,ARRAY['agent-chat'],$5,$7,$8,$9,'Уточнить первый исполнимый шаг')
        """, cid, body.title, body.description, body.project_id, body.agent_id or chat['agent_id'], body.priority, body.curator_agent_id, body.required_skills, chat_id)
        if body.agent_id or chat['agent_id']:
            await c.execute("INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text) VALUES($1,$2,'task_created',$3,$4,$5)", "log-" + str(uuid.uuid4())[:12], body.agent_id or chat['agent_id'], cid, body.project_id, "Создана задача из сообщения чата: " + body.title)
    return {"ok": True, "id": cid}

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
    try:
        await r.xadd(stream, {
            "source": "dashboard",
            "agent": "owner",
            "message": body.content,
            "ts": str(datetime.now().timestamp())
        })
    finally:
        await r.aclose()
    return {"ok": True, "stream": stream}

@app.post("/api/agents/{agent_id}/ping")
async def ping_agent(agent_id: str):
    async with pool.acquire() as c:
        await c.execute("UPDATE agents SET last_heartbeat=NOW(), status='active' WHERE id=$1", agent_id)
    return {"ok": True}
