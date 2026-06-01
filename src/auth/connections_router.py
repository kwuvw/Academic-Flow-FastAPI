from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.connection_service import ConnectionDAO
from src.auth.dependencies import get_current_student, get_current_teacher
from src.auth.models import ConnectionStatus, User, UserRole
from src.auth.schemas import (
    SConnectionRequest,
    SConnectionRespond,
    SConnectionUser,
    SMyStudentsResponse,
    SMyTeachersResponse,
)
from src.core.database import get_async_session

router = APIRouter(
    prefix="/auth/connections",
    tags=["Связи студент — преподаватель"],
)


@router.post("/request", response_model=SConnectionUser, status_code=status.HTTP_201_CREATED)
async def request_connection(
    payload: SConnectionRequest,
    student: User = Depends(get_current_student),
    session: AsyncSession = Depends(get_async_session),
):
    if payload.teacher_id == student.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя отправить заявку самому себе",
        )

    teacher = await session.get(User, payload.teacher_id)
    if teacher is None or teacher.role != UserRole.teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден",
        )

    existing = await ConnectionDAO.get_connection(session, student.id, payload.teacher_id)
    if existing is not None:
        if existing.status == ConnectionStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Заявка уже отправлена",
            )
        if existing.status == ConnectionStatus.accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже прикреплены к этому преподавателю",
            )
        existing = await ConnectionDAO.update_status(session, existing, ConnectionStatus.pending)
        return ConnectionDAO.to_connection_user(teacher, existing)

    connection = await ConnectionDAO.create_request(session, student.id, payload.teacher_id)
    return ConnectionDAO.to_connection_user(teacher, connection)


@router.post("/respond", response_model=SConnectionUser)
async def respond_to_connection(
    payload: SConnectionRespond,
    teacher: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    connection = await ConnectionDAO.get_connection_by_id(session, payload.connection_id)
    if connection is None or connection.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена",
        )

    if connection.status != ConnectionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Заявка уже обработана",
        )

    new_status = ConnectionStatus(payload.status)
    connection = await ConnectionDAO.update_status(session, connection, new_status)

    student = await session.get(User, connection.student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Студент не найден",
        )

    return ConnectionDAO.to_connection_user(student, connection)


@router.get("/my-teachers", response_model=SMyTeachersResponse)
async def get_my_teachers(
    student: User = Depends(get_current_student),
    session: AsyncSession = Depends(get_async_session),
):
    data = await ConnectionDAO.build_my_teachers(session, student.id)
    return SMyTeachersResponse(**data)


@router.get("/my-students", response_model=SMyStudentsResponse)
async def get_my_students(
    teacher: User = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_async_session),
):
    data = await ConnectionDAO.build_my_students(session, teacher.id)
    return SMyStudentsResponse(**data)
