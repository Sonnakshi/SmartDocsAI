from datetime import datetime
from typing import Optional, List, Dict, Any

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


# ========== SEARCH ==========


class DocumentSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="Natural language query for semantic search",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional: Search inside a specific document only",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of matching chunks to return (Top-K)",
    )
    min_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold to filter irrelevant chunks",
    )


class DocumentSearchResult(BaseModel):
    chunk_id: Optional[str] = None
    score: float
    document_id: str
    filename: str
    file_type: str
    chunk_index: int
    text: str


# ========== RAG & AI CHAT ==========


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    score: float
    snippet: str


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="User's question to ask the AI about the documents",
    )
    document_id: Optional[str] = Field(
        default=None,
        description="Optional: Search inside a specific document only. Leave empty/null to search across all documents.",
    )
    top_k: int = Field(
        default=4,
        ge=1,
        le=15,
        description="Number of most relevant context chunks to retrieve for the LLM",
    )
    min_score: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold to filter out irrelevant chunks",
    )
    chat_history: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Recent conversation history messages to enable conversational memory (e.g. [{'role': 'user', 'content': '...'}])",
    )


class ChatResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]
    model_used: str