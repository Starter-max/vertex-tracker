#!/usr/bin/env python3.12
import asyncio, asyncpg, httpx, os, subprocess, platform
from dotenv import load_dotenv

load_dotenv('/Volumes/256/digital-corp/core/.env')
DB = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"

async def latest_pypi(name):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f'https://pypi.org/pypi/{name}/json')
        return r.json()['info']['version']

async def latest_github(owner, repo):
    async with httpx.AsyncClient(timeout=10, headers={'Accept':'application/vnd.github+json'}) as c:
        r = await c.get(f'https://api.github.com/repos/{owner}/{repo}/releases/latest')
        if r.status_code == 200:
            return r.json().get('tag_name') or r.json().get('name')
        r = await c.get(f'https://api.github.com/repos/{owner}/{repo}/tags')
        if r.status_code == 200 and r.json():
            return r.json()[0].get('name')
    return None

async def installed_python_version():
    return platform.python_version()

async def run():
    conn = await asyncpg.connect(DB)
    rows = await conn.fetch('SELECT * FROM knowledge_items ORDER BY category, id')
    for row in rows:
        iid = row['id']
        current = row['current_version']
        latest = current
        status = 'ok'
        score = 100
        if iid == 'infra.fastapi':
            latest = await latest_pypi('fastapi')
            status = 'unknown' if not latest else ('ok' if latest == current else 'outdated')
            score = 50 if not latest else (100 if latest == current else 70)
        elif iid == 'infra.python':
            latest = await installed_python_version()
            status = 'ok'
            score = 100 if latest.startswith('3.12') else 80
        elif iid in ('framework.google-adk', 'framework.langgraph', 'framework.crewai', 'framework.moai-adk'):
            repos = {
                'framework.google-adk': ('google', 'adk-python'),
                'framework.langgraph': ('langchain-ai', 'langgraph'),
                'framework.crewai': ('crewAIInc', 'crewAI'),
                'framework.moai-adk': ('modu-ai', 'moai-adk'),
            }
            latest = await latest_github(*repos[iid])
            status = 'unknown' if not latest else 'outdated'
            score = 50 if not latest else 60
        elif iid.startswith('llm.'):
            latest = current
            status = 'unknown'
            score = 50
        await conn.execute('''
            UPDATE knowledge_items
            SET current_version=$1, latest_version=$2, freshness_score=$3, status=$4, last_checked=NOW(), updated_at=NOW()
            WHERE id=$5
        ''', current, latest, score, status, iid)
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
