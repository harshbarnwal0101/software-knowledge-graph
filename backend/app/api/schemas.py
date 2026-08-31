from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth ───────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Repository ─────────────────────────────────────────────────
class RepositoryCreate(BaseModel):
    github_url: str
    name: Optional[str] = None
    description: Optional[str] = None


class RepositoryOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    github_url: str
    status: str
    status_message: Optional[str]
    total_files: int
    total_lines: int
    total_classes: int
    total_functions: int

    class Config:
        from_attributes = True
