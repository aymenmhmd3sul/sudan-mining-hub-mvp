from fastapi import Request
from app.translations.service import translate, normalize_language


def jinja_translate(request: Request, key: str) -> str:
    lang = normalize_language(getattr(request.state, "lang", "ar"))
    return translate(key, lang)


def template_context(request: Request) -> dict:
    lang = normalize_language(getattr(request.state, "lang", "ar"))

    return {
        "request": request,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "t": lambda key: jinja_translate(request, key),
    }
