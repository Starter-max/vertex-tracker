import asyncio
import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

DEFAULT_PARALLEL_LIMIT = 3


def now_id(prefix: str) -> str:
    return f"{prefix}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _jsonable_row(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


RISKY_WORKER_FLAGS = (
    "destructive",
    "touches_env",
    "touches_secrets",
    "schema_change",
    "production_change",
    "money_spend",
    "deletes_data",
    "changes_gateway",
    "changes_telegram",
)


def evaluate_worker_guardrails(allow_cli: bool, work_package: Dict[str, Any], subtask_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Pure safety gate for real Hermes CLI worker execution.

    Dry-run is always allowed. Real CLI execution requires diagnostics, backup when
    requested, and an explicit owner decision for risky metadata flags.
    """
    reasons: List[str] = []
    requires_owner_decision = False
    if not allow_cli:
        return {"allowed": True, "reasons": [], "requires_owner_decision": False}
    if not work_package.get("diagnostic_ref"):
        reasons.append("missing_diagnostic_ref")
    if work_package.get("requires_backup", True) and not work_package.get("backup_ref"):
        reasons.append("missing_backup_ref")
    for flag in RISKY_WORKER_FLAGS:
        if bool(subtask_metadata.get(flag)):
            reasons.append(f"risky_flag:{flag}")
            requires_owner_decision = True
    if requires_owner_decision and not subtask_metadata.get("owner_decision_id"):
        reasons.append("missing_owner_decision_for_risk")
    return {"allowed": not reasons, "reasons": reasons, "requires_owner_decision": requires_owner_decision}


def build_work_package_result_summary(subtasks: List[Dict[str, Any]]) -> str:
    counts: Dict[str, int] = {}
    lines: List[str] = []
    for st in subtasks:
        status = str(st.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
        title = str(st.get("title") or st.get("id") or "subtask")[:120]
        if status == "failed":
            detail = f"ERROR {str(st.get('error_summary') or '').strip()}".strip()
        else:
            detail = str(st.get("result_summary") or st.get("error_summary") or status).strip()
        lines.append(f"- {title}: {detail[:500]}")
    ordered = ["done", "failed", "needs_review", "running", "queued", "blocked", "cancelled"]
    count_text = ", ".join(f"{k}={counts[k]}" for k in ordered if k in counts)
    return ("Work package summary: " + (count_text or "no subtasks") + "\n" + "\n".join(lines))[:8000]


def split_into_subtasks(objective: str, requested: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Deterministic decomposition for owner-visible MVP.

    If caller provides subtasks, normalize them. Otherwise create the safety-first
    diagnostic -> backup -> implementation -> verification graph required by the
    owner's ТЗ.
    """
    if requested:
        result = []
        for i, item in enumerate(requested, start=1):
            title = str(item.get("title") or f"Subtask {i}").strip()
            result.append({
                "title": title,
                "instructions": str(item.get("instructions") or title).strip(),
                "assignee_agent_id": item.get("assignee_agent_id") or item.get("agent_id"),
                "assignee_profile": item.get("assignee_profile") or item.get("profile"),
                "priority": item.get("priority") or "P2",
                "parallel_group_id": item.get("parallel_group_id") or "main",
                "dependency_ids": item.get("dependency_ids") or [],
                "metadata": item.get("metadata") or {},
            })
        return result

    return [
        {
            "title": "diagnostics: confirm active runtime, schema and delivery targets",
            "instructions": "Read-only diagnostics. Confirm Hermes gateway, Telegram, dashboard, PostgreSQL, Redis, kanban, skills, profiles and cron delivery before changing code.",
            "assignee_agent_id": "anton",
            "assignee_profile": "default",
            "priority": "P1",
            "parallel_group_id": "safety",
            "dependency_ids": [],
            "metadata": {"phase": "diagnostics", "destructive": False},
        },
        {
            "title": "backups: create rollback package without exposing secrets",
            "instructions": "Create config, DB, Redis, skills and git diff backups. Do not print or modify .env/secrets.",
            "assignee_agent_id": "anton",
            "assignee_profile": "default",
            "priority": "P1",
            "parallel_group_id": "safety",
            "dependency_ids": ["diagnostics"],
            "metadata": {"phase": "backup", "destructive": False},
        },
        {
            "title": "implementation: build additive parallel task layer",
            "instructions": objective,
            "assignee_agent_id": "anton",
            "assignee_profile": "default",
            "priority": "P1",
            "parallel_group_id": "build",
            "dependency_ids": ["backups"],
            "metadata": {"phase": "implementation", "destructive": False},
        },
        {
            "title": "verification: smoke-test APIs, DB rows, Redis events and owner summary",
            "instructions": "Verify action->data roundtrip. Report what is production flow vs MVP/test flow. Do not mark complete without diagnostics and backups references.",
            "assignee_agent_id": "anton",
            "assignee_profile": "default",
            "priority": "P1",
            "parallel_group_id": "verify",
            "dependency_ids": ["implementation"],
            "metadata": {"phase": "verification", "destructive": False},
        },
    ]


async def ensure_parallel_migration(pool, migrations_dir):
    path = migrations_dir / "008_parallel_subagents.sql"
    if path.exists():
        async with pool.acquire() as c:
            await c.execute(path.read_text())
            await c.execute("""
                INSERT INTO projects(id,name,type,status,budget_daily,budget_monthly)
                VALUES ('corp','Digital Corp','internal','active',2.50,60.00)
                ON CONFLICT (id) DO NOTHING
            """)
            await c.execute("""
                INSERT INTO agents(id,project_id,name,role,status)
                VALUES ('parallel-engine','corp','Parallel Engine','system_worker','configured')
                ON CONFLICT (id) DO UPDATE SET
                    project_id=COALESCE(agents.project_id, EXCLUDED.project_id),
                    name=EXCLUDED.name,
                    role=EXCLUDED.role,
                    status=COALESCE(NULLIF(agents.status,''), EXCLUDED.status)
            """)


async def emit_event(pool, redis_url: str, event_type: str, message: str, work_package_id: Optional[str] = None,
                     subtask_id: Optional[str] = None, agent_id: Optional[str] = None,
                     severity: str = "info", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}
    event_id = now_id("pevt")
    async with pool.acquire() as c:
        await c.execute(
            """
            INSERT INTO parallel_events(id,event_type,work_package_id,subtask_id,agent_id,severity,message,payload)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb)
            """,
            event_id, event_type, work_package_id, subtask_id, agent_id, severity, message, json.dumps(payload, ensure_ascii=False)
        )
        if work_package_id:
            await c.execute(
                """
                INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                SELECT $1, COALESCE($2,'parallel-engine'), $3, wp.kanban_card_id, wp.project_id, $4
                FROM work_packages wp WHERE wp.id=$5
                ON CONFLICT (id) DO NOTHING
                """,
                event_id, agent_id, event_type, message, work_package_id
            )
    try:
        r = aioredis.from_url(redis_url, decode_responses=True)
        stream = "corp:parallel_events"
        await r.xadd(stream, {
            "event_id": event_id,
            "event_type": event_type,
            "work_package_id": work_package_id or "",
            "subtask_id": subtask_id or "",
            "agent_id": agent_id or "",
            "severity": severity,
            "message": message,
            "payload": json.dumps(payload, ensure_ascii=False),
        }, maxlen=5000, approximate=True)
        if work_package_id:
            await r.xadd("corp:kanban_events", {
                "event_id": event_id,
                "work_package_id": work_package_id,
                "message": message,
                "ts": datetime.utcnow().isoformat(),
            }, maxlen=5000, approximate=True)
        await r.aclose()
    except Exception:
        pass
    return {"id": event_id, "event_type": event_type, "message": message}


async def create_work_package(pool, redis_url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    title = str(body.get("title") or "Parallel work package").strip()
    objective = str(body.get("objective") or title).strip()
    project_id = body.get("project_id") or "corp"
    priority = body.get("priority") or "P2"
    parallel_limit = int(body.get("parallel_limit") or DEFAULT_PARALLEL_LIMIT)
    backup_ref = body.get("backup_ref")
    diagnostic_ref = body.get("diagnostic_ref")
    metadata = body.get("metadata") or {}
    wp_id = body.get("id") or now_id("wp")
    kanban_id = body.get("kanban_card_id") or now_id("kc_parallel")
    subtasks = split_into_subtasks(objective, body.get("subtasks"))

    async with pool.acquire() as c:
        async with c.transaction():
            await c.execute(
                """
                INSERT INTO work_packages(id,title,objective,project_id,kanban_card_id,status,priority,parallel_limit,backup_ref,diagnostic_ref,metadata)
                VALUES($1,$2,$3,$4,NULL,'queued',$5,$6,$7,$8,$9::jsonb)
                ON CONFLICT (id) DO UPDATE SET updated_at=NOW()
                """,
                wp_id, title, objective, project_id, priority, parallel_limit,
                backup_ref, diagnostic_ref, json.dumps(metadata, ensure_ascii=False)
            )
            await c.execute(
                """
                INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,metadata,work_package_id,parallel_group_id,kanban_master_id,next_step)
                VALUES($1,$2,$3,'parallel_work_package','operational',$4,'parallel-engine','queue',$5,ARRAY['parallel','subagents'],$6::jsonb,$7,'root','pepe',$8)
                ON CONFLICT (id) DO UPDATE SET work_package_id=EXCLUDED.work_package_id, updated_at=NOW()
                """,
                kanban_id, title, objective, project_id, priority,
                json.dumps({"source": "parallel_engine", "parallel_limit": parallel_limit}, ensure_ascii=False),
                wp_id, "awaiting dispatcher / owner-visible tracking"
            )
            await c.execute("UPDATE work_packages SET kanban_card_id=$1, updated_at=NOW() WHERE id=$2", kanban_id, wp_id)

            phase_to_id: Dict[str, str] = {}
            created = []
            for item in subtasks:
                phase = (item.get("metadata") or {}).get("phase")
                sid = now_id("st")
                if phase:
                    phase_to_id[phase] = sid
                raw_deps = item.get("dependency_ids") or []
                deps = [phase_to_id.get(dep, dep) for dep in raw_deps]
                await c.execute(
                    """
                    INSERT INTO subtasks(id,work_package_id,title,instructions,assignee_agent_id,assignee_profile,status,priority,parallel_group_id,dependency_ids,metadata)
                    VALUES($1,$2,$3,$4,$5,$6,'queued',$7,$8,$9,$10::jsonb)
                    """,
                    sid, wp_id, item["title"], item["instructions"], item.get("assignee_agent_id"),
                    item.get("assignee_profile"), item.get("priority") or priority, item.get("parallel_group_id"),
                    deps, json.dumps(item.get("metadata") or {}, ensure_ascii=False)
                )
                await c.execute(
                    """
                    INSERT INTO kanban_cards(id,title,description,card_type,layer,project_id,agent_id,status,priority,tags,metadata,work_package_id,subagent_id,parallel_group_id,parent_task_id,assigned_agent_id,required_skills,next_step)
                    VALUES($1,$2,$3,'parallel_subtask','operational',$4,$5,'queue',$6,ARRAY['parallel','subtask'],$7::jsonb,$8,$9,$10,$11,$12,$13::jsonb,$14)
                    """,
                    f"kc_{sid}", item["title"], item["instructions"], project_id,
                    item.get("assignee_agent_id") or "parallel-engine", item.get("priority") or priority,
                    json.dumps({"source": "parallel_engine", "dependency_ids": deps}, ensure_ascii=False),
                    wp_id, item.get("assignee_agent_id"), item.get("parallel_group_id"), kanban_id,
                    item.get("assignee_agent_id"), json.dumps([], ensure_ascii=False), "queued"
                )
                created.append({"id": sid, "title": item["title"], "status": "queued", "dependency_ids": deps})

    await emit_event(pool, redis_url, "work_package_created", f"Created work package: {title}", wp_id, payload={"subtasks": len(created)})
    return await get_work_package(pool, wp_id)


async def get_work_package(pool, work_package_id: str) -> Dict[str, Any]:
    async with pool.acquire() as c:
        wp = await c.fetchrow("SELECT * FROM work_packages WHERE id=$1", work_package_id)
        if not wp:
            return {}
        subs = await c.fetch("SELECT * FROM subtasks WHERE work_package_id=$1 ORDER BY created_at", work_package_id)
        events = await c.fetch("SELECT * FROM parallel_events WHERE work_package_id=$1 ORDER BY created_at DESC LIMIT 50", work_package_id)
    out = _jsonable_row(wp)
    out["subtasks"] = [_jsonable_row(s) for s in subs]
    out["events"] = [_jsonable_row(e) for e in events]
    return out


async def list_work_packages(pool, status: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    q = "SELECT * FROM work_packages WHERE 1=1"
    args = []
    if status:
        args.append(status); q += f" AND status=${len(args)}"
    if project_id:
        args.append(project_id); q += f" AND project_id=${len(args)}"
    args.append(limit); q += f" ORDER BY created_at DESC LIMIT ${len(args)}"
    async with pool.acquire() as c:
        rows = await c.fetch(q, *args)
    return [_jsonable_row(r) for r in rows]


async def dispatch_ready_subtasks(pool, redis_url: str, work_package_id: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Claim ready queued subtasks without launching heavy external processes.

    This is the safe dispatcher primitive for the next ТЗ step: it honors per-package
    parallel_limit and dependency_ids, makes progress visible in DB/kanban/Redis, and
    leaves actual Hermes subprocess execution for a separately verified worker.
    """
    claimed: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    async with pool.acquire() as c:
        packages = await c.fetch(
            """
            SELECT * FROM work_packages
            WHERE status IN ('queued','running')
              AND ($1::text IS NULL OR id=$1::text)
            ORDER BY priority ASC, created_at ASC
            LIMIT 25
            """,
            work_package_id,
        )
        for wp in packages:
            wp_limit = int(limit or wp["parallel_limit"] or DEFAULT_PARALLEL_LIMIT)
            running = await c.fetchval(
                "SELECT COUNT(*) FROM subtasks WHERE work_package_id=$1 AND status='running'",
                wp["id"],
            )
            slots = max(0, wp_limit - int(running or 0))
            if slots <= 0:
                blocked.append({"work_package_id": wp["id"], "reason": "parallel_limit_reached", "parallel_limit": wp_limit})
                continue
            queued = await c.fetch(
                "SELECT * FROM subtasks WHERE work_package_id=$1 AND status IN ('queued','blocked') ORDER BY created_at ASC",
                wp["id"],
            )
            done_ids = set(await c.fetchval(
                "SELECT COALESCE(array_agg(id), ARRAY[]::text[]) FROM subtasks WHERE work_package_id=$1 AND status='done'",
                wp["id"],
            ) or [])
            for st in queued:
                deps = list(st["dependency_ids"] or [])
                missing = [d for d in deps if d not in done_ids]
                if missing:
                    await c.execute(
                        """
                        UPDATE subtasks SET status='blocked', updated_at=NOW() WHERE id=$1 AND status='queued'
                        """,
                        st["id"],
                    )
                    await c.execute(
                        "UPDATE kanban_cards SET status='blocked', next_step=$2, updated_at=NOW() WHERE id=$1",
                        f"kc_{st['id']}", f"waiting dependencies: {', '.join(missing)}",
                    )
                    blocked.append({"id": st["id"], "work_package_id": wp["id"], "reason": "waiting_dependencies", "dependency_ids": missing})
                    continue
                if slots <= 0:
                    break
                if st["status"] == "blocked":
                    await c.execute(
                        "UPDATE subtasks SET status='queued', updated_at=NOW() WHERE id=$1 AND status='blocked'",
                        st["id"],
                    )
                    await c.execute(
                        "UPDATE kanban_cards SET status='queue', next_step='dependencies satisfied; ready for dispatcher', updated_at=NOW() WHERE id=$1",
                        f"kc_{st['id']}",
                    )
                instance_id = now_id("agentinst")
                agent_id = st["assignee_agent_id"] or "parallel-engine"
                display_agent_id = agent_id
                await c.execute(
                    """
                    INSERT INTO agent_instances(id,agent_id,profile_name,status,current_work_package_id,current_subtask_id,last_heartbeat,metadata)
                    VALUES($1,$2,$3,'running',$4,$5,NOW(),$6::jsonb)
                    """,
                    instance_id, agent_id, st["assignee_profile"], wp["id"], st["id"],
                    json.dumps({"dispatcher": "safe_tick", "launch_mode": "claim_only", "display_agent_id": display_agent_id}, ensure_ascii=False),
                )
                await c.execute(
                    """
                    UPDATE subtasks
                    SET status='running', started_at=COALESCE(started_at,NOW()), updated_at=NOW(), metadata=metadata || $2::jsonb
                    WHERE id=$1
                    """,
                    st["id"], json.dumps({"agent_instance_id": instance_id}, ensure_ascii=False),
                )
                await c.execute(
                    """
                    UPDATE kanban_cards
                    SET status='running', subagent_id=$2, last_agent_activity_at=NOW(), moved_at=NOW(), next_step='dispatcher claimed; awaiting worker execution', updated_at=NOW()
                    WHERE id=$1
                    """,
                    f"kc_{st['id']}", display_agent_id,
                )
                await c.execute(
                    """
                    UPDATE work_packages
                    SET status='running', started_at=COALESCE(started_at,NOW()), updated_at=NOW()
                    WHERE id=$1
                    """,
                    wp["id"],
                )
                await c.execute(
                    "UPDATE kanban_cards SET status='running', updated_at=NOW(), moved_at=NOW() WHERE id=$1",
                    wp["kanban_card_id"],
                )
                await c.execute(
                    """
                    INSERT INTO agent_activity_log(id,agent_id,event_type,task_id,project_id,text)
                    VALUES($1,$2,'parallel_subtask_claimed',$3,$4,$5)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    now_id("log"), agent_id, f"kc_{st['id']}", wp["project_id"], f"Dispatcher claimed subtask: {st['title']}",
                )
                claimed.append({"id": st["id"], "work_package_id": wp["id"], "agent_id": display_agent_id, "agent_instance_id": instance_id, "title": st["title"]})
                slots -= 1
    for item in claimed:
        await emit_event(pool, redis_url, "subtask_claimed", f"Dispatcher claimed subtask: {item['title']}", item["work_package_id"], subtask_id=item["id"], agent_id=item["agent_id"], payload={"agent_instance_id": item["agent_instance_id"], "launch_mode": "claim_only"})
    for item in blocked:
        await emit_event(pool, redis_url, "subtask_blocked", f"Subtask blocked: {item.get('reason')}", item.get("work_package_id"), subtask_id=item.get("id"), severity="warning", payload=item)
    return {"ok": True, "claimed": claimed, "blocked": blocked, "claimed_count": len(claimed), "blocked_count": len(blocked), "launch_mode": "claim_only"}


async def execute_running_subtasks(
    pool,
    redis_url: str,
    work_package_id: Optional[str] = None,
    max_items: int = 1,
    allow_cli: bool = False,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    """Bounded worker tick for already-claimed subtasks.

    Safe default is dry-run: it exercises the same durable write path without
    launching Hermes. Real execution is opt-in with allow_cli=True, max_items cap,
    and timeout. This keeps owner-visible observability while preventing surprise
    background agent fan-out.
    """
    max_items = max(1, min(int(max_items or 1), 5))
    timeout_seconds = max(15, min(int(timeout_seconds or 120), 600))
    tick_started_at = datetime.utcnow()
    executed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    failed_count = 0
    timeout_count = 0
    guardrail_blocked_count = 0
    async with pool.acquire() as c:
        rows = await c.fetch(
            """
            SELECT st.*, wp.project_id, wp.title AS work_package_title,
                   wp.requires_backup, wp.backup_ref, wp.diagnostic_ref
            FROM subtasks st
            JOIN work_packages wp ON wp.id = st.work_package_id
            WHERE st.status='running'
              AND ($1::text IS NULL OR st.work_package_id=$1::text)
            ORDER BY st.updated_at ASC, st.created_at ASC
            LIMIT $2
            """,
            work_package_id,
            max_items,
        )
    for st in rows:
        raw_metadata = st["metadata"] or {}
        if isinstance(raw_metadata, str):
            try:
                metadata = json.loads(raw_metadata)
            except Exception:
                metadata = {"raw": raw_metadata}
        else:
            metadata = dict(raw_metadata)
        agent_id = st["assignee_agent_id"] or "parallel-engine"
        mode = "hermes_cli" if allow_cli else "dry_run"
        guardrail = evaluate_worker_guardrails(
            allow_cli=allow_cli,
            work_package={
                "diagnostic_ref": st["diagnostic_ref"],
                "backup_ref": st["backup_ref"],
                "requires_backup": st["requires_backup"],
            },
            subtask_metadata=metadata,
        )
        if not guardrail["allowed"]:
            guardrail_blocked_count += 1
            reason_text = ", ".join(guardrail["reasons"])
            async with pool.acquire() as c:
                decision_id = now_id("od")
                await c.execute(
                    """
                    INSERT INTO owner_decisions(id,work_package_id,question,options,status,response)
                    VALUES($1,$2,$3,$4::jsonb,'pending',$5)
                    """,
                    decision_id,
                    st["work_package_id"],
                    "Worker guardrails blocked real CLI execution; approve, revise, or keep dry_run?",
                    json.dumps(["approve_cli_after_review", "revise_subtask", "keep_dry_run", "cancel"], ensure_ascii=False),
                    reason_text[:1000],
                )
            await update_subtask_status(pool, redis_url, st["id"], "needs_review", result_summary=f"Guardrail blocked allow_cli=true: {reason_text}")
            skipped.append({"id": st["id"], "reason": "guardrail_blocked", "guardrail_reasons": guardrail["reasons"]})
            await emit_event(pool, redis_url, "subtask_guardrail_blocked", f"Worker guardrail blocked subtask: {st['title']}", st["work_package_id"], subtask_id=st["id"], agent_id=agent_id, severity="warning", payload={"reasons": guardrail["reasons"], "mode": mode})
            continue
        prompt = (
            "Ты bounded worker Digital Corp. Выполни только эту подзадачу безопасно.\n"
            f"Work package: {st['work_package_title']} ({st['work_package_id']})\n"
            f"Subtask: {st['title']} ({st['id']})\n"
            f"Instructions: {st['instructions']}\n"
            "Ограничения: не менять .env/секреты, не удалять данные, не менять схему БД, не трогать gateway/Telegram. "
            "Если нужен рискованный шаг — верни NEEDS_OWNER_DECISION и причину. "
            "В конце дай краткий result_summary."
        )
        started_at = datetime.utcnow()
        try:
            if allow_cli:
                env = os.environ.copy()
                env["PATH"] = "/Users/admin/.local/bin:" + env.get("PATH", "")
                proc = await asyncio.create_subprocess_exec(
                    "/Users/admin/.local/bin/hermes",
                    "chat",
                    "-q",
                    prompt,
                    "--quiet",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    timeout_count += 1
                    proc.kill()
                    await proc.communicate()
                    raise RuntimeError(f"Hermes worker timeout after {timeout_seconds}s")
                out = (stdout or b"").decode(errors="ignore").strip()
                err = (stderr or b"").decode(errors="ignore").strip()
                if proc.returncode != 0:
                    raise RuntimeError((err or out or f"Hermes exited {proc.returncode}")[:2000])
                result_summary = out[-4000:] if out else "Hermes worker completed with empty output."
                if "NEEDS_OWNER_DECISION" in result_summary:
                    async with pool.acquire() as c:
                        await c.execute(
                            """
                            INSERT INTO owner_decisions(id,work_package_id,question,options,status,response)
                            VALUES($1,$2,$3,$4::jsonb,'pending',$5)
                            """,
                            now_id("od"), st["work_package_id"], "Worker requested owner decision before continuing",
                            json.dumps(["approve", "revise", "cancel"], ensure_ascii=False), result_summary[:1000],
                        )
                    await update_subtask_status(pool, redis_url, st["id"], "needs_review", result_summary=result_summary)
                    skipped.append({"id": st["id"], "reason": "needs_owner_decision"})
                    continue
            else:
                result_summary = (
                    "DRY_RUN worker tick: subtask execution path verified without launching Hermes CLI. "
                    f"Title='{st['title']}'. Instructions length={len(st['instructions'] or '')}."
                )
            await update_subtask_status(pool, redis_url, st["id"], "done", result_summary=result_summary)
            executed.append({
                "id": st["id"],
                "work_package_id": st["work_package_id"],
                "agent_id": agent_id,
                "mode": mode,
                "duration_seconds": round((datetime.utcnow() - started_at).total_seconds(), 2),
            })
            await emit_event(pool, redis_url, "subtask_executed", f"Worker completed subtask: {st['title']}", st["work_package_id"], subtask_id=st["id"], agent_id=agent_id, payload={"mode": mode})
        except Exception as e:
            failed_count += 1
            await update_subtask_status(pool, redis_url, st["id"], "failed", error_summary=str(e)[:2000])
            skipped.append({"id": st["id"], "reason": "worker_failed", "error": str(e)[:500]})
            await emit_event(pool, redis_url, "subtask_worker_failed", f"Worker failed subtask: {st['title']}", st["work_package_id"], subtask_id=st["id"], agent_id=agent_id, severity="error", payload={"error": str(e)[:1000], "mode": mode})
    duration_seconds = round((datetime.utcnow() - tick_started_at).total_seconds(), 2)
    worker_metrics = {
        "mode": "hermes_cli" if allow_cli else "dry_run",
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "failed_count": failed_count,
        "timeout_count": timeout_count,
        "guardrail_blocked_count": guardrail_blocked_count,
        "duration_seconds": duration_seconds,
        "max_items": max_items,
        "timeout_seconds": timeout_seconds,
    }
    await emit_event(pool, redis_url, "worker_tick_summary", "Worker tick summary", work_package_id, payload=worker_metrics)
    return {
        "ok": True,
        **worker_metrics,
        "executed": executed,
        "skipped": skipped,
    }


async def update_subtask_status(pool, redis_url: str, subtask_id: str, status: str, result_summary: Optional[str] = None, error_summary: Optional[str] = None) -> Dict[str, Any]:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT * FROM subtasks WHERE id=$1", subtask_id)
        if not row:
            return {}
        wp_id = row["work_package_id"]
        await c.execute(
            """
            UPDATE subtasks
            SET status=$2,
                result_summary=COALESCE($3,result_summary),
                error_summary=COALESCE($4,error_summary),
                started_at=CASE WHEN $2='running' AND started_at IS NULL THEN NOW() ELSE started_at END,
                completed_at=CASE WHEN $2 IN ('done','failed','cancelled') THEN NOW() ELSE completed_at END,
                updated_at=NOW()
            WHERE id=$1
            """,
            subtask_id, status, result_summary, error_summary
        )
        await c.execute(
            """
            UPDATE kanban_cards
            SET status=$1,
                result_summary=COALESCE($2,result_summary),
                updated_at=NOW(),
                moved_at=NOW(),
                last_agent_activity_at=NOW()
            WHERE work_package_id=$3 AND id=$4
            """,
            status, result_summary, wp_id, f"kc_{subtask_id}"
        )
        counts = await c.fetchrow(
            """
            SELECT COUNT(*) total,
                   COUNT(*) FILTER (WHERE status='done') done,
                   COUNT(*) FILTER (WHERE status='failed') failed,
                   COUNT(*) FILTER (WHERE status='needs_review') needs_review,
                   COUNT(*) FILTER (WHERE status IN ('running','queued','blocked','needs_review')) open
            FROM subtasks WHERE work_package_id=$1
            """,
            wp_id
        )
        subtasks_for_summary = await c.fetch(
            "SELECT id,title,status,result_summary,error_summary FROM subtasks WHERE work_package_id=$1 ORDER BY created_at",
            wp_id,
        )
        aggregate_summary = build_work_package_result_summary([_jsonable_row(s) for s in subtasks_for_summary])
        wp_status = None
        if counts["failed"] or counts["needs_review"]:
            wp_status = "needs_review"
        elif counts["total"] and counts["done"] == counts["total"]:
            wp_status = "done"
        elif status == "running":
            wp_status = "running"
        if wp_status:
            await c.execute(
                """
                UPDATE work_packages
                SET status=$2,
                    result_summary=$3,
                    completed_at=CASE WHEN $2='done' THEN NOW() ELSE completed_at END,
                    updated_at=NOW()
                WHERE id=$1
                """,
                wp_id, wp_status, aggregate_summary
            )
            await c.execute("UPDATE kanban_cards SET status=$2, updated_at=NOW(), moved_at=NOW() WHERE work_package_id=$1 AND card_type='parallel_work_package'", wp_id, wp_status)
    await emit_event(pool, redis_url, "subtask_status", f"Subtask {subtask_id} -> {status}", wp_id, subtask_id=subtask_id, severity="error" if status == "failed" else "info")
    return await get_work_package(pool, wp_id)
