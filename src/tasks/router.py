import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.auth.dependencies import get_current_teacher, get_current_user
from src.auth.models import ConnectionStatus, User, UserConnection
from src.database import get_async_session
from src.tasks.models import Task

router = APIRouter(
    prefix="/api/tasks",
    tags=["Задания"],
)

# Директория для файлов заданий, разрешённые расширения и лимит 10 МБ
UPLOAD_DIR = os.path.join("src", "frontend", "static", "uploads", "tasks")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _serialize_task(t: Task) -> dict:
    """Сериализация задачи в JSON-словарь для API."""
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

    now = datetime.now(timezone.utc)
    # Определяем статус задачи по дедлайну:
    # active — дедлайн ещё не наступил (deadline >= now)
    # completed — дедлайн прошёл, но прошло не более 7 дней (now - 7д <= deadline < now)
    task_status = "active"
    if t.deadline:
        if t.deadline < now:
            # Дедлайн прошёл — задача завершена, если прошло не более 7 дней
            if (now - t.deadline).days <= 7:
                task_status = "completed"
            else:
                # Более 7 дней — к удалению (не должен попасть в выборку)
                task_status = "expired"

    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "deadline": t.deadline.isoformat() if t.deadline else None,
        "created_at": t.created_at.isoformat(),
        "group_name": t.group_name,
        "course_number": t.course_number,
        "file_path": file_path,
        "file_original_name": file_original_name,
        "teacher_name": teacher_name,
        "status": task_status,
    }


@router.get("/list")
async def list_tasks(
    status_filter: str = Query("active", alias="status", pattern="^(active|completed)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получение списка заданий с фильтрацией по статусу.
    - active: дедлайн ещё не наступил (deadline >= now)
    - completed: дедлайн прошёл, но не более 7 дней назад
    Для студентов — задания их группы/курса.
    Для преподавателей — задания, которые они выдали.
    """
    now = datetime.now(timezone.utc)

    if current_user.role == "student":
        # Студент видит задания своей группы и курса
        base_filter = and_(
            Task.group_name == current_user.group_name,
            Task.course_number == current_user.course_number,
        )
    else:
        # Преподаватель видит задания, которые он создал
        base_filter = Task.teacher_id == current_user.id

    if status_filter == "active":
        # Активные: дедлайн ещё не наступил
        time_filter = Task.deadline >= now
    else:
        # Завершённые: дедлайн прошёл, но прошло не более 7 дней
        seven_days_ago = now - timedelta(days=7)
        time_filter = and_(Task.deadline < now, Task.deadline >= seven_days_ago)

    task_query = (
        select(Task)
        .where(base_filter, time_filter)
        .options(joinedload(Task.teacher))
        .order_by(Task.created_at.desc())
    )
    result = await session.execute(task_query)
    tasks_raw = list(result.scalars().all())

    return [_serialize_task(t) for t in tasks_raw]


@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_tasks(
    session: AsyncSession = Depends(get_async_session),
):
    """
    Удаление заданий, у которых deadline < (текущая_дата - 7 дней).
    Можно вызывать вручную или через фоновую задачу.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    # Находим задания, просроченные более 7 дней
    query = select(Task).where(Task.deadline < cutoff)
    result = await session.execute(query)
    expired_tasks = list(result.scalars().all())

    if not expired_tasks:
        return {"status": "success", "message": "Нет заданий для удаления", "deleted": 0}

    deleted_count = 0
    for task in expired_tasks:
        # Удаляем файлы задания с диска
        if task.file_paths:
            try:
                paths = json.loads(task.file_paths)
                for p in paths:
                    full_path = os.path.join("src", "frontend", p.lstrip("/"))
                    if os.path.exists(full_path):
                        os.remove(full_path)
            except (json.JSONDecodeError, TypeError, OSError):
                pass
        await session.delete(task)
        deleted_count += 1

    await session.commit()
    return {"status": "success", "message": f"Удалено заданий: {deleted_count}", "deleted": deleted_count}


@router.get("/my-groups")
async def get_my_groups(
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    conn_query = select(UserConnection.student_id).where(
        UserConnection.teacher_id == current_user.id,
        UserConnection.status == ConnectionStatus.accepted,
    )
    conn_result = await session.execute(conn_query)
    student_ids = list(conn_result.scalars().all())

    if not student_ids:
        return []

    students_q = select(User).where(
        User.id.in_(student_ids),
        User.role == "student",
        User.group_name.isnot(None),
        User.group_name != "",
    )
    result = await session.execute(students_q)
    students = result.scalars().all()

    groups_map: dict[tuple[str, int], str] = {}
    for s in students:
        key = (s.group_name, s.course_number or 0)
        if key not in groups_map:
            label = f"{s.course_number}-" if s.course_number else ""
            label += s.group_name
            groups_map[key] = label

    return [
        {"group_name": gn, "course_number": cn, "label": lbl}
        for (gn, cn), lbl in sorted(groups_map.items(), key=lambda x: (x[0][1], x[0][0]))
    ]


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_task(
    title: str = Form(""),
    description: str = Form(""),
    deadline: str = Form(""),
    course_number: str = Form("0"),
    group_name: str = Form(""),
    files: list[UploadFile] = File(default=None),
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        if not title or not title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Название задания обязательно.",
            )

        if not group_name or not group_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Название группы обязательно.",
            )

        parsed_deadline = None
        if deadline and deadline.strip():
            try:
                parsed_deadline = datetime.fromisoformat(deadline.strip())
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Неверный формат даты: {deadline}. Используйте YYYY-MM-DDTHH:MM.",
                )

        parsed_course = None
        if course_number and course_number.strip():
            try:
                val = int(course_number.strip())
                if val > 0:
                    parsed_course = val
            except (ValueError, TypeError):
                parsed_course = None

        saved_paths = []
        original_names = []

        if files:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            for upload_file in files:
                if not upload_file or not upload_file.filename:
                    continue

                original_filename = upload_file.filename
                file_content = await upload_file.read()
                file_size = len(file_content)

                if file_size == 0:
                    continue

                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Файл '{original_filename}' слишком большой (макс 10 МБ).",
                    )

                ext = os.path.splitext(original_filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Недопустимый формат '{ext}'. Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                    )

                # UUID-имя файла для избежания коллизий и подмены
                safe_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(UPLOAD_DIR, safe_name)

                with open(file_path, "wb") as f:
                    f.write(file_content)

                saved_paths.append(f"/static/uploads/tasks/{safe_name}")
                original_names.append(original_filename)

        file_paths_json = json.dumps(saved_paths) if saved_paths else None
        original_names_json = json.dumps(original_names) if original_names else None

        task = Task(
            teacher_id=current_user.id,
            course_number=parsed_course,
            group_name=group_name.strip(),
            title=title.strip(),
            description=description.strip() if description and description.strip() else None,
            deadline=parsed_deadline,
            file_paths=file_paths_json,
            file_original_name=original_names_json,
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        return {
            "status": "success",
            "message": "Задание создано",
            "id": task.id,
            "title": task.title,
            "group_name": task.group_name,
            "course_number": task.course_number,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "file_paths": saved_paths,
            "file_original_names": original_names,
            "created_at": task.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании задания: {str(e)}",
        )


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Task).where(Task.id == task_id, Task.teacher_id == current_user.id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено или у вас нет прав для его удаления.",
        )

    if task.file_paths:
        try:
            paths = json.loads(task.file_paths)
            for p in paths:
                full_path = os.path.join("src", "frontend", p.lstrip("/"))
                if os.path.exists(full_path):
                    os.remove(full_path)
        except (json.JSONDecodeError, TypeError, OSError):
            pass

    await session.delete(task)
    await session.commit()

    return {"status": "success", "message": "Задание удалено"}


@router.post("/{task_id}/complete", status_code=status.HTTP_200_OK)
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Принудительное завершение задания преподавателем (ручное удаление).
    Задание удаляется немедленно, минуя 7-дневный срок хранения.
    """
    query = select(Task).where(Task.id == task_id, Task.teacher_id == current_user.id)
    result = await session.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Задание не найдено или у вас нет прав.",
        )

    if task.file_paths:
        try:
            paths = json.loads(task.file_paths)
            for p in paths:
                full_path = os.path.join("src", "frontend", p.lstrip("/"))
                if os.path.exists(full_path):
                    os.remove(full_path)
        except (json.JSONDecodeError, TypeError, OSError):
            pass

    await session.delete(task)
    await session.commit()

    return {"status": "success", "message": "Задание завершено"}
