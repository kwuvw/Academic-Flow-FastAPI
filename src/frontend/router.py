import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from src.auth.dependencies import get_current_user, get_current_teacher, get_optional_user
from src.auth.models import ConnectionStatus, User, UserConnection
from src.database import get_async_session
from src.tasks.models import Task

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
    tasks = []
    nearest_deadline = "--.--"
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

        task_query = (
            select(Task)
            .where(
                Task.group_name == user.group_name,
                Task.course_number == user.course_number,
            )
            .options(joinedload(Task.teacher))
            .order_by(Task.created_at.desc())
        )
        result = await session.execute(task_query)
        tasks_raw = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        tasks = []
        for t in tasks_raw:
            file_path = None
            file_original_name = None
            if t.file_paths:
                try:
                    paths = json.loads(t.file_paths)
                    if paths:
                        file_path = paths[0]
                except (json.JSONDecodeError, TypeError):
                    pass
            if t.file_original_name:
                try:
                    names = json.loads(t.file_original_name)
                    if names:
                        file_original_name = names[0]
                except (json.JSONDecodeError, TypeError):
                    pass
            teacher_name = None
            if t.teacher:
                parts = [t.teacher.first_name, t.teacher.last_name]
                teacher_name = " ".join(p for p in parts if p)

            is_burning = False
            if t.deadline and t.deadline >= now and (t.deadline - now).days < 7:
                is_burning = True

            tasks.append({
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "deadline": t.deadline,
                "created_at": t.created_at,
                "file_path": file_path,
                "file_original_name": file_original_name,
                "teacher_name": teacher_name,
                "is_burning": is_burning,
            })

        closest_task_query = (
            select(Task)
            .where(
                Task.group_name == user.group_name,
                Task.course_number == user.course_number,
                Task.deadline >= now,
            )
            .order_by(Task.deadline.asc())
            .limit(1)
        )
        closest_task_result = await session.execute(closest_task_query)
        closest_task = closest_task_result.scalar_one_or_none()
        nearest_deadline = closest_task.deadline.strftime("%d.%m") if closest_task else "--.--"

    return render_template(
        request,
        "dashboard_student.html",
        user=user,
        title="Academic Flow | Кабинет студента",
        user_role="student",
        active_page="/dashboard/student",
        teachers=teachers,
        tasks=tasks,
        nearest_deadline=nearest_deadline,
        now=datetime.now(timezone.utc),
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


@router.get("/tasks/my", response_class=HTMLResponse)
async def my_tasks_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    now = datetime.now(timezone.utc)
    task_query = (
        select(Task)
        .where(
            Task.group_name == current_user.group_name,
            Task.course_number == current_user.course_number,
        )
        .options(joinedload(Task.teacher))
        .order_by(Task.created_at.desc())
    )
    result = await session.execute(task_query)
    tasks_raw = list(result.scalars().all())

    tasks = []
    for t in tasks_raw:
        file_path = None
        file_original_name = None
        if t.file_paths:
            try:
                paths = json.loads(t.file_paths)
                if paths:
                    file_path = paths[0]
            except (json.JSONDecodeError, TypeError):
                pass
        if t.file_original_name:
            try:
                names = json.loads(t.file_original_name)
                if names:
                    file_original_name = names[0]
            except (json.JSONDecodeError, TypeError):
                pass
        teacher_name = None
        if t.teacher:
            parts = [t.teacher.first_name, t.teacher.last_name]
            teacher_name = " ".join(p for p in parts if p)

        is_burning = False
        if t.deadline and t.deadline >= now and (t.deadline - now).days < 7:
            is_burning = True

        tasks.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline,
            "created_at": t.created_at,
            "file_path": file_path,
            "file_original_name": file_original_name,
            "teacher_name": teacher_name,
            "is_burning": is_burning,
        })

    return render_template(
        request,
        "tasks_student.html",
        user=current_user,
        title="Academic Flow | Задания",
        user_role="student",
        active_page="/tasks/my",
        tasks=tasks,
        now=datetime.now(timezone.utc),
    )


@router.get("/tasks/burning", response_class=HTMLResponse)
async def burning_tasks_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    now = datetime.now(timezone.utc)
    one_week_later = now + timedelta(days=7)

    task_query = (
        select(Task)
        .where(
            Task.group_name == current_user.group_name,
            Task.course_number == current_user.course_number,
            Task.deadline >= now,
            Task.deadline <= one_week_later,
        )
        .options(joinedload(Task.teacher))
        .order_by(Task.deadline.asc())
    )
    result = await session.execute(task_query)
    tasks_raw = list(result.scalars().all())

    tasks = []
    for t in tasks_raw:
        file_path = None
        file_original_name = None
        if t.file_paths:
            try:
                paths = json.loads(t.file_paths)
                if paths:
                    file_path = paths[0]
            except (json.JSONDecodeError, TypeError):
                pass
        if t.file_original_name:
            try:
                names = json.loads(t.file_original_name)
                if names:
                    file_original_name = names[0]
            except (json.JSONDecodeError, TypeError):
                pass
        teacher_name = None
        if t.teacher:
            parts = [t.teacher.first_name, t.teacher.last_name]
            teacher_name = " ".join(p for p in parts if p)

        tasks.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline,
            "created_at": t.created_at,
            "file_path": file_path,
            "file_original_name": file_original_name,
            "teacher_name": teacher_name,
            "is_burning": True,
        })

    return render_template(
        request,
        "burning_tasks.html",
        user=current_user,
        title="Academic Flow | Горишь🔥",
        user_role="student",
        active_page="/tasks/burning",
        tasks=tasks,
        now=datetime.now(timezone.utc),
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
