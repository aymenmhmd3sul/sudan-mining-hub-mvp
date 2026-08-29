from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.translations.templates import template_context

router = APIRouter(tags=["UI"])

templates = Jinja2Templates(directory="app/templates")


def render(request: Request, template_name: str, title_key: str):
    context = template_context(request)
    context["title"] = context["t"](title_key)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


@router.get("/login")
def login_page(request: Request):
    return render(
        request,
        "auth/login.html",
        "pages.login.title",
    )


@router.get("/marketplace")
def marketplace_page(request: Request):
    return render(
        request,
        "marketplace/marketplace.html",
        "pages.marketplace.title",
    )


@router.get("/requests")
def requests_page(request: Request):
    return render(
        request,
        "requests/requests.html",
        "pages.requests.title",
    )


@router.get("/negotiation")
def negotiation_page(request: Request):
    return render(
        request,
        "negotiation/negotiation.html",
        "pages.negotiation.title",
    )


@router.get("/services")
def services_page(request: Request):
    return render(
        request,
        "services/services.html",
        "pages.services.title",
    )
