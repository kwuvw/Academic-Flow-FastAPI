from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.models import User, UserRole
from src.auth.schemas import SUserRegister
from src.auth.utils import get_password_hash


class UserDAO:
    @classmethod
    async def find_by_email(cls, session: AsyncSession, email: str):
        query = select(User).filter(User.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @classmethod
    async def add_user(cls, session: AsyncSession, user_data: SUserRegister):
        hashed_pwd = get_password_hash(user_data.password)
        
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_pwd,
            role=UserRole(user_data.role),
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user