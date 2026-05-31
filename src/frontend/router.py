from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Frontend"])
templates = Jinja2Templates(directory="src/frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Academic Flow | Главная"},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "Academic Flow | Вход"},
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"title": "Academic Flow | Регистрация"},
    )


@router.get("/dashboard/student", response_class=HTMLResponse)
async def student_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard_student.html",
        context={"title": "Academic Flow | Кабинет студента"},
    )


@router.get("/dashboard/teacher", response_class=HTMLResponse)
async def teacher_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard_teacher.html",
        context={"title": "Academic Flow | Кабинет преподавателя"},
    )
