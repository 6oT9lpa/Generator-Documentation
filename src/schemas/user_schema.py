from pydantic import BaseModel, EmailStr, Field, validator, model_validator
from typing import Optional
import re

class UserBase(BaseModel):
    username: str = Field(max_length=50, min_length=3)

class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(min_length=8)
    password_confirm: str

class UserLogin(BaseModel):
    username: Optional[str] = Field(None, max_length=50, min_length=3)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=8)

    @validator('username')
    def username_validator(cls, v):
        if v is not None and not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores and hyphens")
        return v

    @model_validator(mode='after')
    def check_username_or_email(self) -> 'UserLogin':
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided")
        return self

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class UserInDB(UserBase):
    id: str
    hashed_password: str

    class Config:
        from_attributes = True

class RefreshTokenRequest(BaseModel):
    refresh_token: str
