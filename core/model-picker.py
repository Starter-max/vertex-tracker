#!/usr/bin/env python3
"""
model-picker.py — выбирает лучшую модель с OpenRouter.

Приоритет:
1. Бесплатные модели, отсортированные по context_length (больше = мощнее)
2. Если бесплатные исчерпаны — платные с лучшим price/context ratio
3. Исключает модели из чёрного списка (которые уже не работали)

Использование:
    python3 model-picker.py              # выбрать и вывести модель
    python3 model-picker.py --apply      # выбрать и записать в config.yaml
    python3 model-picker.py --blacklist openrouter/owl-alpha  # добавить в чёрный список
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
CONFIG_PATH = os.path.expanduser("~/.hermes/config.yaml")
BLACKLIST_PATH = os.path.expanduser("~/.hermes/.model_blacklist")
PICKED_PATH = os.path.expanduser("~/.hermes/.model_picked")
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def load_blacklist():
    if os.path.exists(BLACKLIST_PATH):
        with open(BLACKLIST_PATH) as f:
            return set(line.strip() for line in f if line.strip())
    return set()


def save_blacklist(blacklist):
    with open(BLACKLIST_PATH, "w") as f:
        for m in sorted(blacklist):
            f.write(m + "\n")


def add_to_blacklist(model_id):
    blacklist = load_blacklist()
    blacklist.add(model_id)
    save_blacklist(blacklist)
    print(f"Added {model_id} to blacklist")


def load_picked():
    if os.path.exists(PICKED_PATH):
        with open(PICKED_PATH) as f:
            return json.load(f)
    return {"date": "", "model": "", "blacklist": []}


def save_picked(model_id):
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "model": model_id,
        "blacklist": list(load_blacklist()),
    }
    with open(PICKED_PATH, "w") as f:
        json.dump(data, f, indent=2)


def fetch_models():
    req = urllib.request.Request(OPENROUTER_MODELS_URL)
    if OPENROUTER_API_KEY:
        req.add_header("Authorization", f"Bearer {OPENROUTER_API_KEY}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def is_free(model):
    p = model.get("pricing", {})
    return p.get("prompt", "1") == "0" and p.get("completion", "1") == "0"


def score_free(model):
    """Чем выше тем лучше: большой контекст = мощнее модель."""
    return model.get("context_length", 0)


def score_paid(model):
    """Лучшее соотношение цена/контекст для платных моделей."""
    ctx = model.get("context_length", 1)
    prompt_price = float(model.get("pricing", {}).get("prompt", "0.01"))
    completion_price = float(model.get("pricing", {}).get("completion", "0.01"))
    avg_price = (prompt_price + completion_price) / 2
    if avg_price == 0:
        return float("inf")
    return ctx / avg_price  # больше контекст, меньше цена = лучше


def pick_model():
    blacklist = load_blacklist()
    picked = load_picked()
    today = datetime.now().strftime("%Y-%m-%d")

    # Если сегодня уже выбрали — возвращаем ту же
    if picked["date"] == today and picked["model"] and picked["model"] not in blacklist:
        return picked["model"], "cached"

    models = fetch_models()
    all_models = models.get("data", [])

    # Фильтруем: не в чёрном списке, не аудио/видео/изображения
    text_models = [
        m for m in all_models
        if m["id"] not in blacklist
        and "audio" not in m["id"].lower()
        and "vision" not in m["id"].lower()
        and "image" not in m["id"].lower()
        and "video" not in m["id"].lower()
    ]

    # 1. Бесплатные — сортируем по контексту (больше = мощнее)
    free = sorted(
        [m for m in text_models if is_free(m)],
        key=score_free,
        reverse=True,
    )

    if free:
        best = free[0]
        return best["id"], "free"

    # 2. Платные — лучшее соотношение цена/контекст
    paid = sorted(
        [m for m in text_models if not is_free(m)],
        key=score_paid,
        reverse=True,
    )

    if paid:
        best = paid[0]
        return best["id"], "paid"

    return None, "none"


def apply_to_config(model_id):
    """Записывает модель в config.yaml"""
    import re

    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}")
        return False

    with open(CONFIG_PATH) as f:
        content = f.read()

    # Заменяем model.default
    new_content = re.sub(
        r"^(\s*default:\s*).*$",
        rf"\1{model_id}",
        content,
        flags=re.MULTILINE,
    )

    if new_content == content:
        print("Warning: model.default not found in config")
        return False

    with open(CONFIG_PATH, "w") as f:
        f.write(new_content)

    return True


def main():
    # Обработка --blacklist
    if "--blacklist" in sys.argv:
        idx = sys.argv.index("--blacklist")
        if idx + 1 < len(sys.argv):
            add_to_blacklist(sys.argv[idx + 1])
            return
        else:
            print("Usage: model-picker.py --blacklist <model_id>")
            sys.exit(1)

    model_id, source = pick_model()

    if not model_id:
        print("ERROR: No suitable model found!")
        sys.exit(1)

    print(f"model={model_id}")
    print(f"source={source}")

    if "--apply" in sys.argv:
        if apply_to_config(model_id):
            save_picked(model_id)
            print(f"Applied {model_id} to {CONFIG_PATH}")
        else:
            print("Failed to apply model to config")
            sys.exit(1)


if __name__ == "__main__":
    main()
