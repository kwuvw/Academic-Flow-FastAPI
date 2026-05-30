from pydantic import BaseModel, EmailStr, Field


class SUserRegister(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта пользователя")
    password: str = Field(..., min_length=6, max_length=50, description="Пароль от 6 до 50 символов")


class SUserLogin(BaseModel):
    email: EmailStr
    password: str


class SUserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool


    class Config:
        from_attributes = True