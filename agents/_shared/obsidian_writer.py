import os
from pathlib import Path
from filelock import FileLock
from datetime import datetime

VAULT = Path(os.getenv("OBSIDIAN_VAULT", "/Volumes/256/digital-corp/obsidian-vault"))

class ObsidianWriter:
    def write_daily(self, project: str, content: str):
        date = datetime.now().strftime("%Y-%m-%d")
        path = VAULT / f"Projects/{project}/Daily/{date}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {date}\n\n{content}\n")

    def append(self, rel_path: str, content: str):
        path = VAULT / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(str(path) + ".lock")
        with lock:
            with open(path, "a") as f:
                f.write(f"\n{content}")
