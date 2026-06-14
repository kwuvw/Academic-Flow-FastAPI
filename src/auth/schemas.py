import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SUserRegister(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта пользователя")
    password: str = Field(..., min_length=6, max_length=50, description="Пароль от 6 до 50 символов")
    role: Literal["student", "teacher"] = Field(..., description="Роль пользователя")

    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    middle_name: str | None = Field(None, max_length=100, description="Отчество")
    group_name: str | None = Field(None, max_length=50, description="Название группы (для студентов)")
    course_number: int | None = Field(None, ge=1, le=6, description="Номер курса (для студентов)")
    department: str | None = Field(None, max_length=200, description="Кафедра (для преподавателей)")


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
    is_admin: bool = False
    is_approved: bool = True

    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    group_name: str | None = None
    course_number: int | None = None
    department: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SUpdateProfile(BaseModel):
    first_name: str | None = Field(None, max_length=100, description="Имя")
    last_name: str | None = Field(None, max_length=100, description="Фамилия")
    middle_name: str | None = Field(None, max_length=100, description="Отчество")
    group_name: str | None = Field(None, max_length=50, description="Название группы (для студентов)")
    course_number: int | None = Field(None, ge=1, le=4, description="Номер курса (для студентов)")
    department: str | None = Field(None, max_length=200, description="Кафедра (для преподавателей)")

    @field_validator("first_name", "last_name", "middle_name")
    @classmethod
    def _validate_name_cyrillic(cls, v):
        if v is not None and v != "" and not re.match(r"^[а-яёА-ЯЁ\s\-]+$", v):
            raise ValueError("Допустимы только буквы (кириллица), пробелы и дефисы")
        return v

    @field_validator("group_name")
    @classmethod
    def _validate_group(cls, v):
        allowed = {"ГД", "Д", "ИЗ", "ИС", "КМ", "Т", "СА", "Р", "ПП", "ОН", "БУХ", "МС"}
        if v is not None and v != "" and v not in allowed:
            raise ValueError(f"Допустимые группы: {', '.join(sorted(allowed))}")
        return v


class SConnectionUser(BaseModel):
    id: int
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    group_name: str | None = None
    course_number: int | None = None
    department: str | None = None
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
