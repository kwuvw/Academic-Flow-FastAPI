from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import ConnectionStatus, User, UserConnection, UserRole
from src.database import get_async_session
from src.tasks.models import Task

router = APIRouter(
    prefix="/api/admin",
    tags=["Админ-панель"],
)


def require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для администраторов",
        )


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    require_admin(current_user)

    students = await session.execute(
        select(func.count()).select_from(User).where(User.role == UserRole.student)
    )
    teachers = await session.execute(
        select(func.count()).select_from(User).where(
            User.role == UserRole.teacher,
            User.is_approved == True,
        )
    )

    groups_q = await session.execute(
        select(func.count(func.distinct(User.group_name))).select_from(User).where(
            User.role == UserRole.student,
            User.group_name.isnot(None),
            User.group_name != "",
        )
    )

    tasks_q = await session.execute(
        select(func.count()).select_from(Task)
    )

    return {
        "total_students": students.scalar() or 0,
        "total_teachers": teachers.scalar() or 0,
        "total_groups": groups_q.scalar() or 0,
        "total_tasks": tasks_q.scalar() or 0,
    }


@router.get("/users")
async def get_users(
    role: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    require_admin(current_user)

    query = select(User)
    if role == "student":
        query = query.where(User.role == UserRole.student)
    elif role == "teacher":
        query = query.where(User.role == UserRole.teacher)
    query = query.order_by(User.id.desc())

    result = await session.execute(query)
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name or "",
            "last_name": u.last_name or "",
            "middle_name": u.middle_name or "",
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "is_admin": u.is_admin,
            "is_approved": u.is_approved,
            "group_name": u.group_name or "",
            "course_number": u.course_number,
            "department": u.department or "",
        }
        for u in users
    ]


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    require_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя",
        )

    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    await session.delete(user)
    await session.commit()
    return {"detail": "Пользователь удалён"}


@router.get("/groups")
async def get_groups(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    require_admin(current_user)

    students_q = await session.execute(
        select(User).where(
            User.role == UserRole.student,
            User.group_name.isnot(None),
            User.group_name != "",
        )
    )
    students = list(students_q.scalars().all())

    groups_map: dict[tuple[str, int], list[User]] = {}
    for s in students:
        key = (s.group_name or "—", s.course_number or 0)
        groups_map.setdefault(key, []).append(s)

    conn_q = await session.execute(
        select(UserConnection).where(UserConnection.status == ConnectionStatus.accepted)
    )
    connections = list(conn_q.scalars().all())

    teacher_for_student: dict[int, int] = {}
    for c in connections:
        teacher_for_student[c.student_id] = c.teacher_id

    teacher_ids_needed = set(teacher_for_student.values())
    teachers_map: dict[int, str] = {}
    if teacher_ids_needed:
        teachers_q = await session.execute(
            select(User).where(User.id.in_(teacher_ids_needed))
        )
        for t in teachers_q.scalars().all():
            parts = [t.last_name, t.first_name, t.middle_name]
            teachers_map[t.id] = " ".join(p for p in parts if p) or t.email

    result = []
    for (group_name, course_number), members in sorted(
        groups_map.items(), key=lambda x: (x[0][1], x[0][0])
    ):
        teacher_names = set()
        for m in members:
            tid = teacher_for_student.get(m.id)
            if tid and tid in teachers_map:
                teacher_names.add(teachers_map[tid])

        result.append({
            "group_name": group_name,
            "course_number": course_number,
            "student_count": len(members),
            "teacher_names": sorted(teacher_names),
        })

    return result
