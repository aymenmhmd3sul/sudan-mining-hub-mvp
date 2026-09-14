import app.db.base  # CENTRAL ORM REGISTRY — SINGLE SOURCE OF TRUTH
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, ui, admin, deals, offers, requests
from app.routers import marketplace
from app.translations.middleware import LanguageMiddleware
from app.translations.templates import template_context


app = FastAPI(title="Sudan Mining Hub MVP")


@app.exception_handler(403)
async def subscription_ui_forbidden(request: Request, exc):
    if (
        request.url.path not in {"/auth/login", "/auth/register"}
        and request.headers.get("accept", "").find("text/html") >= 0
        and getattr(exc, "detail", None) == "Active subscription required"
    ):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url="/?subscription_required=1",
            status_code=303,
        )

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=403,
        content={"detail": exc.detail},
    )


app.add_middleware(LanguageMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/static/uploads"), name="uploads")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(ui.router)


@app.get("/")
def read_root(request: Request):
    context = template_context(request)
    context["title"] = "Sudan Mining Hub"

    return templates.TemplateResponse(
        request=request,
        name="gateway/gateway.html",
        context=context,
    )

app.include_router(admin.router)
app.include_router(deals.router)

app.include_router(offers.router)
app.include_router(requests.router)
app.include_router(marketplace.router)
