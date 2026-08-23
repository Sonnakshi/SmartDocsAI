from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ========== USERS ==========


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)


class UserResponse(UserBase):
    id: str
    role: str


class UserInDB(UserBase):
    id: str
    hashed_password: str
    role: str = "user"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


# ========== AUTH ==========


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ========== DOCUMENTS ==========


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    owner_id: str
    size_bytes: int
    word_count: int
    character_count: int
    chunk_count: int
    uploaded_at: datetime
    download_url: str
    file_url: str        # S3 URL (public or presigned)
    s3_key: str          # S3 object key for deletion


class DocumentListResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    owner_id: str
    size_bytes: int
    word_count: int
    character_count: int
    chunk_count: int
    uploaded_at: datetime
    download_url: str
    file_url: str
    s3_key: str


class DocumentSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query for semantic search",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of matching chunks to return",
    )


class DocumentSearchResult(BaseModel):
    score: float
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    text: str