import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def load_translations(lang: str) -> dict:
    if lang not in {"ar", "en"}:
        lang = "ar"

    path = BASE_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def translate(key: str, lang: str = "ar") -> str:
    return load_translations(lang).get(key, key)
