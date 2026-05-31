from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SUserRegister(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта пользователя")
    password: str = Field(..., min_length=6, max_length=50, description="Пароль от 6 до 50 символов")
    role: Literal["student", "teacher"] = Field(..., description="Роль пользователя")


class SUserLogin(BaseModel):
    email: EmailStr
    password: str


class SUserResponse(BaseModel):
    id: int
    email: EmailStr
    role: Literal["student", "teacher"]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SUserMeResponse(BaseModel):
    id: int
    email: EmailStr
    role: Literal["student", "teacher"]
    is_active: bool
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
