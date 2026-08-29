from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.translations.service import normalize_language


class LanguageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        language = request.cookies.get("language", "ar")
        request.state.lang = normalize_language(language)

        response = await call_next(request)

        response.set_cookie(
            key="language",
            value=request.state.lang,
            httponly=False,
            samesite="lax",
        )

        return response
