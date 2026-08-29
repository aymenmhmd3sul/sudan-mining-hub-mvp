from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, ui
from app.translations.middleware import LanguageMiddleware
from app.translations.templates import template_context


app = FastAPI(title="Sudan Mining Hub MVP")

app.add_middleware(LanguageMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
