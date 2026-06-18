"""Persistance locale : config + etat. Tout reste sur le disque, jamais transmis."""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULTS = {
    "target_minutes": 120,   # objectif de visionnage par chaine
    "mute": True,
    "headless": False,       # False = fenetre Chrome visible (login + controle)
    "selected_channels": [],  # slugs choisis au menu
}


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_config() -> dict:
    _ensure_dir()
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data if isinstance(data, dict) else {})
        return merged
    except Exception:
        return dict(DEFAULTS)


def save_config(config: dict) -> None:
    _ensure_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
