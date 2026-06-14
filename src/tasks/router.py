import json
import os
import uuid
import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_teacher
from src.auth.models import User
from src.database import get_async_session
from src.tasks.models import Task

router = APIRouter(
    prefix="/api/tasks",
    tags=["Задания"],
)

UPLOAD_DIR = os.path.join("src", "frontend", "static", "uploads", "tasks")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024


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
            except (ValueError, TypeError) as e:
                print(f"[tasks/create] Ошибка парсинга даты '{deadline}': {e}")
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
                print(f"[tasks/create] Не удалось распарсить course_number: '{course_number}'")
                parsed_course = None

        saved_paths = []
        original_names = []

        if files:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            for upload_file in files:
                if not upload_file or not upload_file.filename:
                    print(f"[tasks/create] Пропущен файл без filename: {upload_file}")
                    continue

                original_filename = upload_file.filename
                print(f"[tasks/create] Обработка файла: filename='{original_filename}'")

                file_content = await upload_file.read()
                file_size = len(file_content)

                if file_size == 0:
                    print(f"[tasks/create] Пропущен пустой файл: {original_filename}")
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

                safe_name = f"{uuid.uuid4().hex}{ext}"
                file_path = os.path.join(UPLOAD_DIR, safe_name)

                with open(file_path, "wb") as f:
                    f.write(file_content)

                saved_paths.append(f"/static/uploads/tasks/{safe_name}")
                original_names.append(original_filename)
                print(f"[tasks/create] Файл сохранён: {file_path}, оригинальное имя: '{original_filename}'")

        file_paths_json = json.dumps(saved_paths) if saved_paths else None
        original_names_json = json.dumps(original_names) if original_names else None

        print(f"[tasks/create] Перед сохранением в БД:")
        print(f"  file_paths_json = {file_paths_json}")
        print(f"  original_names_json = {original_names_json}")

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

        print(f"[tasks/create] Задание создано: id={task.id}")
        print(f"[tasks/create] Проверка из БД: file_original_name='{task.file_original_name}'")

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
        print(f"[tasks/create] НЕОЖИДАННАЯ ОШИБКА: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании задания: {str(e)}",
        )
