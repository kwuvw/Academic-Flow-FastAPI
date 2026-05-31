from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import SUserLogin, SUserMeResponse, SUserRegister, SUserResponse
from src.auth.service import UserDAO
from src.auth.utils import create_access_token, verify_password
from src.core.database import get_async_session

router = APIRouter(
    prefix="/auth",
    tags=["Аутентификация"],
)


@router.post("/register", response_model=SUserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: SUserRegister,
    session: AsyncSession = Depends(get_async_session),
):
    existing_user = await UserDAO.find_by_email(session, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегестрирован",
        )

    new_user = await UserDAO.add_user(session, user_data)
    return new_user


@router.post("/login")
async def login_user(
    user_data: SUserLogin,
    session: AsyncSession = Depends(get_async_session),
):
    user = await UserDAO.find_by_email(session, user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная почта или пароль",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
    }


@router.get("/me", response_model=SUserMeResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user
