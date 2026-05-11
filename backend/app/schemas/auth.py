from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.password import validate_bcrypt_password_bytes


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_bcrypt_password_bytes(value)
