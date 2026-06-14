import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.schemas import SUpdateProfile, SUserLogin, SUserMeResponse, SUserRegister, SUserResponse
from src.auth.service import UserDAO
from src.auth.utils import create_access_token, verify_password
from src.database import get_async_session

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

    response = JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
    })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,
        path="/",
        samesite="lax",
    )
    return response


@router.get("/me", response_model=SUserMeResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout():
    response = JSONResponse({"detail": "Logged out"})
    response.delete_cookie(key="access_token", path="/")
    return response


@router.put("/profile/update", response_model=SUserMeResponse)
async def update_profile(
    update_data: SUpdateProfile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if update_data.course_number is not None and not 1 <= update_data.course_number <= 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер курса должен быть от 1 до 4",
        )

    name_pattern = re.compile(r"^[а-яёА-ЯЁ\s\-]+$")
    for field_name in ("first_name", "last_name", "middle_name"):
        value = getattr(update_data, field_name, None)
        if value and not name_pattern.match(value):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Поле «{field_name}» должно содержать только буквы (кириллица)",
            )

    allowed_groups = {"ГД", "Д", "ИЗ", "ИС", "КМ", "Т", "СА", "Р", "ПП", "ОН", "БУХ", "МС"}
    if update_data.group_name and update_data.group_name not in allowed_groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Допустимые группы: {', '.join(sorted(allowed_groups))}",
        )

    filtered_data = update_data.model_dump(exclude_unset=True)
    if filtered_data:
        current_user = await UserDAO.update_user(session, current_user, filtered_data)
    return current_user
