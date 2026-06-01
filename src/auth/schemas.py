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


class SConnectionUser(BaseModel):
    id: int
    email: EmailStr
    connection_id: int | None = None
    status: Literal["pending", "accepted", "rejected"] | None = None

    model_config = ConfigDict(from_attributes=True)


class SMyTeachersResponse(BaseModel):
    accepted: list[SConnectionUser]
    pending: list[SConnectionUser]
    all_teachers: list[SConnectionUser]


class SMyStudentsResponse(BaseModel):
    accepted: list[SConnectionUser]
    pending: list[SConnectionUser]


class SConnectionRequest(BaseModel):
    teacher_id: int = Field(..., gt=0)


class SConnectionRespond(BaseModel):
    connection_id: int = Field(..., gt=0)
    status: Literal["accepted", "rejected"]
