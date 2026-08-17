from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/")
def show_form(request: Request):
    return templates.TemplateResponse("ticket_form.html", {"request": request})