from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, get_current_teacher, get_optional_user
from src.auth.models import ConnectionStatus, User, UserConnection
from src.core.database import get_async_session

router = APIRouter(tags=["Frontend"])
templates = Jinja2Templates(directory="src/frontend/templates")


def render_template(request: Request, name: str, user: User | None = None, **context):
    context["request"] = request
    context["user"] = user
    return templates.TemplateResponse(request=request, name=name, context=context)


@router.get("/", response_class=HTMLResponse)
async def index_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    return render_template(request, "index.html", user=user, title="Academic Flow | Главная")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "teacher":
        return RedirectResponse(url="/dashboard/teacher")
    return RedirectResponse(url="/dashboard/student")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render_template(request, "login.html", title="Academic Flow | Вход")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render_template(request, "register.html", title="Academic Flow | Регистрация")


@router.get("/dashboard/student", response_class=HTMLResponse)
async def student_dashboard(
    request: Request,
    user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_async_session),
):
    teachers = []
    if user:
        query = select(UserConnection).where(
            UserConnection.student_id == user.id,
            UserConnection.status == ConnectionStatus.accepted,
        )
        result = await session.execute(query)
        connections = list(result.scalars().all())
        teacher_ids = [c.teacher_id for c in connections]
        if teacher_ids:
            query = select(User).where(User.id.in_(teacher_ids))
            result = await session.execute(query)
            teachers = list(result.scalars().all())

    return render_template(
        request,
        "dashboard_student.html",
        user=user,
        title="Academic Flow | Кабинет студента",
        user_role="student",
        active_page="/dashboard/student",
        teachers=teachers,
    )


@router.get("/dashboard/teacher", response_class=HTMLResponse)
async def teacher_dashboard(
    request: Request,
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    query = (
        select(UserConnection, User)
        .join(User, UserConnection.student_id == User.id)
        .where(
            UserConnection.teacher_id == current_user.id,
            UserConnection.status == ConnectionStatus.accepted,
        )
    )
    result = await session.execute(query)
    rows = result.all()

    students = []
    for connection, student in rows:
        students.append({
            "id": student.id,
            "first_name": student.first_name or "",
            "last_name": student.last_name or "",
            "course_number": student.course_number,
            "group_name": student.group_name or "",
            "connection_id": connection.id,
        })

    return render_template(
        request,
        "dashboard_teacher.html",
        user=current_user,
        title="Academic Flow | Кабинет преподавателя",
        user_role="teacher",
        active_page="/dashboard/teacher",
        students=students,
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    return render_template(
        request,
        "profile.html",
        user=user,
        title="Academic Flow | Профиль",
        user_role=user.role if user else None,
        active_page="/profile",
    )


@router.get("/teachers", response_class=HTMLResponse)
async def teachers_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    return render_template(
        request,
        "teachers.html",
        user=user,
        title="Academic Flow | Преподаватели",
        user_role="student",
        active_page="/teachers",
    )


@router.get("/students", response_class=HTMLResponse)
async def students_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    return render_template(
        request,
        "students.html",
        user=user,
        title="Academic Flow | Студенты",
        user_role="teacher",
        active_page="/students",
    )
