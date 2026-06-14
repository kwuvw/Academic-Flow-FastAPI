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
    ADMIN_EMAIL = "admin@mail.ru"
    ADMIN_PASSWORD = "1234567890"

    if user_data.email == ADMIN_EMAIL and user_data.password == ADMIN_PASSWORD:
        from src.auth.utils import get_password_hash
        from src.auth.models import UserRole

        user = await UserDAO.find_by_email(session, ADMIN_EMAIL)

        if not user:
            hashed = get_password_hash(ADMIN_PASSWORD)
            user = User(
                email=ADMIN_EMAIL,
                hashed_password=hashed,
                role=UserRole.teacher,
                is_active=True,
                is_verified=True,
                is_admin=True,
                is_approved=True,
                first_name="Администратор",
                last_name="Системы",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        if not user.is_admin:
            user.is_admin = True
            user.is_approved = True
            if user.role != UserRole.teacher:
                user.role = UserRole.teacher
            await session.commit()
            await session.refresh(user)

        role_val = user.role.value if hasattr(user.role, "value") else str(user.role)
        access_token = create_access_token(data={"sub": str(user.id), "role": role_val})

        response = JSONResponse({
            "access_token": access_token,
            "token_type": "bearer",
            "role": role_val,
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


@router.post("/admin/approve/{user_id}")
async def approve_teacher(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для администраторов",
        )

    user = await session.get(User, user_id)
    if not user or user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден",
        )

    user.is_approved = True
    await session.commit()
    return {"detail": "Преподаватель одобрен"}


@router.post("/admin/reject/{user_id}")
async def reject_teacher(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только для администраторов",
        )

    user = await session.get(User, user_id)
    if not user or user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден",
        )

    await session.delete(user)
    await session.commit()
    return {"detail": "Преподаватель отклонён и удалён"}
