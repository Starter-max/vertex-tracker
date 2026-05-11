from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from collections import defaultdict
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import asyncpg, psutil, subprocess, asyncio, os, uuid, httpx, redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv("/Volumes/256/digital-corp/core/.env")
DB = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"
FRONTEND = Path("/Volumes/256/digital-corp/dashboard/frontend/index.html")
UPLOADS = Path("/Volumes/256/digital-corp/dashboard/uploads")
UPLOADS.mkdir(exist_ok=True)
pool = None

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
    log_path = Path(f"/Volumes/256/digital-corp/logs/{pid}.log")
    logs = "\n".join(log_path.read_text().splitlines()[-40:]) if log_path.exists() else "нет логов"
    return {**dict(p), "cost_today": float(total or 0), "agents": [dict(a) for a in agents], "logs": logs}

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
            ["hermes", "ask", "--no-stream", message],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:2000]
    except: pass
    return "⚠️ Hermes не подключён. Попробуй: hermes ask 'твой вопрос' в терминале."

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
