#!/usr/bin/env python3.12
"""Запускает только новые миграции. Безопасно запускать повторно."""
import asyncpg, asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv("/Volumes/256/digital-corp/core/.env")
DB = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"
MIGRATIONS_DIR = Path(__file__).parent

async def run():
    conn = await asyncpg.connect(DB)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            filename VARCHAR(100) PRIMARY KEY,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    applied = {r['filename'] for r in await conn.fetch("SELECT filename FROM _migrations")}
    files = sorted(f for f in MIGRATIONS_DIR.glob("*.sql"))
    
    for f in files:
        if f.name in applied:
            print(f"  skip  {f.name}")
            continue
        print(f"  apply {f.name} ...", end=" ")
        try:
            await conn.execute(f.read_text())
            await conn.execute("INSERT INTO _migrations(filename) VALUES($1)", f.name)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    
    await conn.close()
    print("Migrations complete.")

asyncio.run(run())
