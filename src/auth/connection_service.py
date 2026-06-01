from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import ConnectionStatus, User, UserConnection, UserRole
from src.auth.schemas import SConnectionUser


class ConnectionDAO:
    @classmethod
    async def get_connection(
        cls,
        session: AsyncSession,
        student_id: int,
        teacher_id: int,
    ) -> UserConnection | None:
        query = select(UserConnection).where(
            UserConnection.student_id == student_id,
            UserConnection.teacher_id == teacher_id,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_connection_by_id(
        cls,
        session: AsyncSession,
        connection_id: int,
    ) -> UserConnection | None:
        return await session.get(UserConnection, connection_id)

    @classmethod
    async def list_for_student(
        cls,
        session: AsyncSession,
        student_id: int,
    ) -> list[UserConnection]:
        query = select(UserConnection).where(UserConnection.student_id == student_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def list_for_teacher(
        cls,
        session: AsyncSession,
        teacher_id: int,
    ) -> list[UserConnection]:
        query = select(UserConnection).where(UserConnection.teacher_id == teacher_id)
        result = await session.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def list_all_teachers(cls, session: AsyncSession) -> list[User]:
        query = select(User).where(User.role == UserRole.teacher, User.is_active.is_(True))
        result = await session.execute(query)
        return list(result.scalars().all())

    @classmethod
    async def create_request(
        cls,
        session: AsyncSession,
        student_id: int,
        teacher_id: int,
    ) -> UserConnection:
        connection = UserConnection(
            student_id=student_id,
            teacher_id=teacher_id,
            status=ConnectionStatus.pending,
        )
        session.add(connection)
        await session.commit()
        await session.refresh(connection)
        return connection

    @classmethod
    async def update_status(
        cls,
        session: AsyncSession,
        connection: UserConnection,
        status: ConnectionStatus,
    ) -> UserConnection:
        connection.status = status
        await session.commit()
        await session.refresh(connection)
        return connection

    @staticmethod
    def to_connection_user(
        user: User,
        connection: UserConnection | None = None,
    ) -> SConnectionUser:
        return SConnectionUser(
            id=user.id,
            email=user.email,
            connection_id=connection.id if connection else None,
            status=connection.status.value if connection else None,
        )

    @classmethod
    async def build_my_teachers(cls, session: AsyncSession, student_id: int) -> dict:
        connections = await cls.list_for_student(session, student_id)
        connection_by_teacher = {c.teacher_id: c for c in connections}

        teachers = await cls.list_all_teachers(session)
        teacher_ids = {t.id for t in teachers}
        accepted: list[SConnectionUser] = []
        pending: list[SConnectionUser] = []
        all_teachers: list[SConnectionUser] = []

        for teacher in teachers:
            connection = connection_by_teacher.get(teacher.id)
            item = cls.to_connection_user(teacher, connection)
            all_teachers.append(item)
            if connection is None:
                continue
            if connection.status == ConnectionStatus.accepted:
                accepted.append(item)
            elif connection.status == ConnectionStatus.pending:
                pending.append(item)

        for connection in connections:
            if connection.teacher_id not in teacher_ids:
                teacher = await session.get(User, connection.teacher_id)
                if teacher is None:
                    continue
                item = cls.to_connection_user(teacher, connection)
                all_teachers.append(item)
                if connection.status == ConnectionStatus.accepted:
                    accepted.append(item)
                elif connection.status == ConnectionStatus.pending:
                    pending.append(item)

        all_teachers.sort(key=lambda item: item.email)
        accepted.sort(key=lambda item: item.email)
        pending.sort(key=lambda item: item.email)

        return {
            "accepted": accepted,
            "pending": pending,
            "all_teachers": all_teachers,
        }

    @classmethod
    async def build_my_students(cls, session: AsyncSession, teacher_id: int) -> dict:
        connections = await cls.list_for_teacher(session, teacher_id)
        accepted: list[SConnectionUser] = []
        pending: list[SConnectionUser] = []

        for connection in connections:
            student = await session.get(User, connection.student_id)
            if student is None:
                continue
            item = cls.to_connection_user(student, connection)
            if connection.status == ConnectionStatus.accepted:
                accepted.append(item)
            elif connection.status == ConnectionStatus.pending:
                pending.append(item)

        accepted.sort(key=lambda item: item.email)
        pending.sort(key=lambda item: item.email)

        return {"accepted": accepted, "pending": pending}
