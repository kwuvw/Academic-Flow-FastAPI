from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_session 
from src.auth.schemas import SUserRegister, SUserResponse, SUserLogin
from src.auth.service import UserDAO
from src.auth.utils import verify_password, create_access_token

router = APIRouter(
    prefix = "/auth",
    tags = ["Аутентификация"]
)

@router.post("/register", response_model = SUserResponse, status_code = status.HTTP_201_CREATED)
async def register_user(user_data: SUserRegister, session: AsyncSession = Depends(get_async_session)):
    existing_user = await UserDAO.find_by_email(session, user_data.email)
    if existing_user: 
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Пользователь с таким email уже зарегестрирован"
        )
        
    new_user = await UserDAO.add_user(session, user_data)
    return new_user


@router.post("/login")
async def login_user(user_data: SUserLogin, session: AsyncSession = Depends(get_async_session)):
    user = await UserDAO.find_by_email(session, user_data.email)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Неверная почта или пароль"
        )
        
    access_token = create_access_token(data = {"sub": str(user.id)})
        
    return{
        "access_token": access_token,
        "token_type": "bearer"
    }