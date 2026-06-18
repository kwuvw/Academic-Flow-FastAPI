import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
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
        if not current_user.is_approved and not current_user.is_admin:
            return RedirectResponse(url="/waiting-approval")
        return RedirectResponse(url="/dashboard/teacher")
    return RedirectResponse(url="/dashboard/student")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render_template(request, "login.html", title="Academic Flow | Вход")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render_template(request, "register.html", title="Academic Flow | Регистрация")


@router.get("/waiting-approval", response_class=HTMLResponse)
async def waiting_approval_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return render_template(
        request,
        "waiting_approval.html",
        user=current_user,
        title="Academic Flow | Ожидание подтверждения",
    )


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
                parts = [t.teacher.last_name, t.teacher.first_name, t.teacher.middle_name]
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
    if current_user.role == "teacher" and not current_user.is_approved and not current_user.is_admin:
        return templates.TemplateResponse(request=request, name="waiting_approval.html", context={"request": request, "user": current_user})

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
            "middle_name": student.middle_name or "",
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


@router.get("/teacher/groups", response_class=HTMLResponse)
async def teacher_groups_page(
    request: Request,
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    if current_user.role == "teacher" and not current_user.is_approved and not current_user.is_admin:
        return templates.TemplateResponse(request=request, name="waiting_approval.html", context={"request": request, "user": current_user})

    conn_query = select(UserConnection.student_id).where(
        UserConnection.teacher_id == current_user.id,
        UserConnection.status == ConnectionStatus.accepted,
    )
    conn_result = await session.execute(conn_query)
    student_ids = list(conn_result.scalars().all())

    if not student_ids:
        return render_template(
            request,
            "groups_teacher.html",
            user=current_user,
            title="Academic Flow | Группы",
            user_role="teacher",
            active_page="/teacher/groups",
            groups=[],
        )

    query = select(User).where(
        User.id.in_(student_ids),
        User.role == "student",
    )
    result = await session.execute(query)
    all_students = list(result.scalars().all())

    groups_map: dict[tuple[str, int], list[User]] = {}
    for s in all_students:
        key = (s.group_name or "—", s.course_number or 0)
        groups_map.setdefault(key, []).append(s)

    groups = []
    for (group_name, course_number), members in sorted(
        groups_map.items(), key=lambda x: (x[0][1], x[0][0])
    ):
        student_names = []
        for m in members:
            parts = [m.last_name, m.first_name, m.middle_name]
            name = " ".join(p for p in parts if p) or m.email
            student_names.append(name)
        groups.append({
            "group_name": group_name,
            "course_number": course_number,
            "count": len(members),
            "student_names": student_names,
            "initial": group_name[0].upper() if group_name else "Г",
        })

    return render_template(
        request,
        "groups_teacher.html",
        user=current_user,
        title="Academic Flow | Группы",
        user_role="teacher",
        active_page="/teacher/groups",
        groups=groups,
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
            parts = [t.teacher.last_name, t.teacher.first_name, t.teacher.middle_name]
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
            parts = [t.teacher.last_name, t.teacher.first_name, t.teacher.middle_name]
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
    current_user: User = Depends(get_current_teacher),
):
    if current_user.role == "teacher" and not current_user.is_approved and not current_user.is_admin:
        return templates.TemplateResponse(request=request, name="waiting_approval.html", context={"request": request, "user": current_user})

    return render_template(
        request,
        "students.html",
        user=current_user,
        title="Academic Flow | Студенты",
        user_role="teacher",
        active_page="/students",
    )


@router.get("/teacher/tasks", response_class=HTMLResponse)
async def teacher_tasks_page(
    request: Request,
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    if current_user.role == "teacher" and not current_user.is_approved and not current_user.is_admin:
        return templates.TemplateResponse(request=request, name="waiting_approval.html", context={"request": request, "user": current_user})

    now = datetime.now(timezone.utc)

    task_query = (
        select(Task)
        .where(Task.teacher_id == current_user.id)
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

        tasks.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "deadline": t.deadline,
            "created_at": t.created_at,
            "group_name": t.group_name,
            "course_number": t.course_number,
            "file_path": file_path,
            "file_original_name": file_original_name,
        })

    return render_template(
        request,
        "tasks_teacher.html",
        user=current_user,
        title="Academic Flow | Выданные задания",
        user_role="teacher",
        active_page="/teacher/tasks",
        tasks=tasks,
        now=now,
    )


@router.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.is_admin:
        return RedirectResponse(url="/dashboard")

    query = select(User).where(
        User.role == "teacher",
        User.is_approved == False,
    ).order_by(User.id.desc())
    result = await session.execute(query)
    pending_teachers = list(result.scalars().all())

    teachers = []
    for t in pending_teachers:
        parts = [t.last_name, t.first_name, t.middle_name]
        full_name = " ".join(p for p in parts if p) or t.email
        teachers.append({
            "id": t.id,
            "full_name": full_name,
            "email": t.email,
            "department": t.department or "",
        })

    return render_template(
        request,
        "admin_panel.html",
        user=current_user,
        title="Academic Flow | Панель администратора",
        user_role="teacher",
        active_page="/admin/panel",
        pending_teachers=teachers,
    )