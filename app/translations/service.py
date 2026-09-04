import json
from functools import lru_cache
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_LANGUAGES = {"ar", "en"}
DEFAULT_LANGUAGE = "ar"


def normalize_language(lang: Optional[str]) -> str:
    if not lang:
        return DEFAULT_LANGUAGE

    lang = lang.strip().lower()

    if lang in SUPPORTED_LANGUAGES:
        return lang

    return DEFAULT_LANGUAGE


@lru_cache(maxsize=2)
def load_translations(lang: str) -> dict:
    lang = normalize_language(lang)
    path = BASE_DIR / f"{lang}.json"

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    def flatten(value: dict, prefix: str = "") -> dict:
        result = {}
        for key, item in value.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(item, dict):
                result.update(flatten(item, full_key))
            else:
                result[full_key] = item
        return result

    return flatten(data)


def translate(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    translations = load_translations(lang)
    return translations.get(key, key)
