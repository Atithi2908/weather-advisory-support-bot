"""Pydantic schemas for authentication and user accounts."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User's unique email address")
    password: str = Field(..., min_length=6, description="Password with minimum 6 characters")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User's account email")
    password: str = Field(..., description="Plaintext password")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
