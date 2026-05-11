import subprocess, os, sys
from pathlib import Path
from datetime import datetime
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv("/Volumes/256/digital-corp/core/.env")

REPO_PATH = Path("/Volumes/256/digital-corp")
GH_TOKEN  = os.getenv("GITHUB_TOKEN")
GH_USER   = os.getenv("GITHUB_USERNAME", "Starter-max")
gh        = Github(GH_TOKEN)

def run(cmd: str, cwd=REPO_PATH) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return (r.stdout + r.stderr).strip()

# ─── ОПЕРАЦИИ ────────────────────────────────────────────────

def status() -> str:
    """Статус рабочего дерева"""
    return run("git status --short")

def auto_commit(message: str = None) -> str:
    """Закоммитить все изменения"""
    st = run("git status --short")
    if not st:
        return "Нет изменений для коммита"
    run("git add -A")
    # Исключаем .env из коммита
    run("git reset HEAD core/.env 2>/dev/null")
    msg = message or f"chore: auto-commit {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    out = run(f'git commit -m "{msg}"')
    push = run("git push origin main")
    return f"Закоммичено и запушено:\n{out}\n{push}"

def create_tag(version: str, message: str = None) -> str:
    """Создать версионный тег"""
    msg = message or f"Version {version}"
    run(f'git tag -a {version} -m "{msg}"')
    out = run(f"git push origin {version}")
    return f"Тег {version} создан и запушен:\n{out}"

def list_tags() -> str:
    return run("git tag --sort=-version:refname | head -10")

def create_repo(name: str, description: str = "", private: bool = True) -> str:
    """Создать новый GitHub репозиторий"""
    try:
        user = gh.get_user()
        repo = user.create_repo(name=name, description=description, private=private, auto_init=False)
        return f"Репозиторий создан: {repo.html_url}"
    except GithubException as e:
        return f"Ошибка: {e.data.get('message', str(e))}"

def list_repos() -> str:
    """Список репозиториев"""
    user = gh.get_user()
    repos = list(user.get_repos())
    return "\n".join(f"{'🔒' if r.private else '🌐'} {r.name} — {r.html_url}" for r in repos[:20])

def log(n: int = 10) -> str:
    return run(f"git log --oneline -{n}")

def diff() -> str:
    return run("git diff --stat HEAD")

# ─── CLI ─────────────────────────────────────────────────────

COMMANDS = {
    "status":      (status,      "Статус изменений"),
    "commit":      (auto_commit, "Закоммитить всё [сообщение]"),
    "tag":         (create_tag,  "Создать тег <version> [сообщение]"),
    "tags":        (list_tags,   "Список тегов"),
    "create-repo": (create_repo, "Создать репо <name> [description]"),
    "repos":       (list_repos,  "Список репозиториев"),
    "log":         (log,         "Последние коммиты [n]"),
    "diff":        (diff,        "Изменения с последнего коммита"),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("help", "--help"):
        print("Git Manager — команды:")
        for cmd, (fn, desc) in COMMANDS.items():
            print(f"  {cmd:15} {desc}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd not in COMMANDS:
        print(f"Неизвестная команда: {cmd}"); sys.exit(1)
    
    fn = COMMANDS[cmd][0]
    result = fn(*args) if args else fn()
    print(result)
