from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class Registration(StrictSchema):
    email: EmailStr = Field(max_length=254)
    password: SecretStr
    display_name: str = Field(min_length=1, max_length=100)
    role: Literal["CLIENT", "MASTER"] = "CLIENT"

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if len(password) < 10 or len(password.encode("utf-8")) > 72 or "\x00" in password:
            raise ValueError("Пароль: от 10 символов и не более 72 байт UTF-8, без нулевого символа")
        return value

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Введите имя")
        return value.strip()


class Login(StrictSchema):
    email: str = Field(min_length=1, max_length=254)
    password: SecretStr

    @field_validator("password")
    @classmethod
    def bound_password(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) > 1024:
            raise ValueError("Слишком длинный пароль")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    role: Literal["CLIENT", "MASTER", "ADMIN"]


class UserUpdate(StrictSchema):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Введите имя")
        return value.strip()


class TokenRead(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = 900
    user: UserRead


class AccessRead(BaseModel):
    role: str
    message: str
