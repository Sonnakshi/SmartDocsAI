from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional
import uuid

from bson import ObjectId
from docx import Document as DocxDocument
from fastapi import FastAPI, HTTPException, status, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pypdf import PdfReader

from app.schemas import (
    UserCreate,
    UserResponse,
    Token,
    UserUpdate,
    RefreshTokenRequest,
    AccessTokenResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchRequest,
    DocumentSearchResult,
)
from app.database import users_collection, documents_collection
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.utils_chunking import chunk_text
from app.vector_db import (
    store_document_chunks,
    search_document_chunks,
    delete_document_chunks,
)
from app.s3_storage import (
    upload_file_to_s3,
    delete_file_from_s3,
    get_file_stream_from_s3,
)


tags_metadata = [
    {"name": "System", "description": "System health and root endpoints."},
    {"name": "Authentication", "description": "User registration, login, and token refresh endpoints."},
    {"name": "Users", "description": "Endpoints for the currently authenticated user profile."},
    {"name": "Documents", "description": "Upload, list, download, search, and delete documents."},
    {"name": "Admin", "description": "Admin-only endpoints."},
]


app = FastAPI(
    title="SmartDocs AI API",
    description="APIs for authentication, token refresh, user profile management, document upload and processing, and admin-protected user listing.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


def get_file_extension(filename: str) -> str:
    filename = filename.lower()
    if "." not in filename:
        return ""
    return "." + filename.split(".")[-1]


def validate_object_id(document_id: str) -> ObjectId:
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=400, detail="Invalid document ID")
    return ObjectId(document_id)


def extract_text_from_file(content: bytes, extension: str) -> str:
    try:
        if extension == ".txt":
            return content.decode("utf-8", errors="ignore").strip()

        if extension == ".pdf":
            pdf = PdfReader(BytesIO(content))
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages).strip()

        if extension == ".docx":
            doc = DocxDocument(BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs]
            return "\n".join(paragraphs).strip()

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to extract text from the uploaded file",
        )

    raise HTTPException(status_code=400, detail="Unsupported file type")


def build_document_response(doc: dict) -> DocumentResponse:
    document_id = str(doc["_id"])
    return DocumentResponse(
        id=document_id,
        filename=doc["filename"],
        file_type=doc["file_type"],
        owner_id=doc["owner_id"],
        size_bytes=doc["size_bytes"],
        word_count=doc.get("word_count", 0),
        character_count=doc.get("character_count", 0),
        chunk_count=doc.get("chunk_count", 0),
        uploaded_at=doc["uploaded_at"],
        download_url=f"/documents/{document_id}/download",
        file_url=doc["file_url"],
        s3_key=doc["s3_key"],
    )


def build_document_list_response(doc: dict) -> DocumentListResponse:
    document_id = str(doc["_id"])
    return DocumentListResponse(
        id=document_id,
        filename=doc["filename"],
        file_type=doc["file_type"],
        owner_id=doc["owner_id"],
        size_bytes=doc["size_bytes"],
        word_count=doc.get("word_count", 0),
        character_count=doc.get("character_count", 0),
        chunk_count=doc.get("chunk_count", 0),
        uploaded_at=doc["uploaded_at"],
        download_url=f"/documents/{document_id}/download",
        file_url=doc["file_url"],
        s3_key=doc["s3_key"],
    )


def get_media_type(file_type: str) -> str:
    if file_type == "pdf":
        return "application/pdf"
    if file_type == "txt":
        return "text/plain; charset=utf-8"
    if file_type == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


@app.get(
    "/",
    tags=["System"],
    summary="Root endpoint",
    description="Check whether the SmartDocs AI backend is running.",
)
def read_root():
    return {"message": "SmartDocs AI backend is alive"}


@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Check whether the API service is healthy and available.",
)
def health_check():
    return {"status": "ok"}


@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
    summary="Register user",
    description="Create a new user account with email, password, and optional full name.",
)
async def register_user(user: UserCreate):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)

    user_doc = {
        "email": user.email,
        "full_name": user.full_name,
        "hashed_password": hashed_pw,
        "role": "user",
    }

    result = await users_collection.insert_one(user_doc)

    return UserResponse(
        id=str(result.inserted_id),
        email=user.email,
        full_name=user.full_name,
        role="user",
    )


@app.post(
    "/login",
    response_model=Token,
    tags=["Authentication"],
    summary="Login user",
    description="Authenticate a user using email in the username field and return access and refresh tokens.",
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user.get("role", "user")}
    )
    refresh_token = create_refresh_token(data={"sub": str(user["_id"])})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@app.post(
    "/refresh",
    response_model=AccessTokenResponse,
    tags=["Authentication"],
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token.",
)
async def refresh_access_token(refresh_data: RefreshTokenRequest):
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(refresh_data.refresh_token)
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "refresh":
            raise credentials_error
    except JWTError:
        raise credentials_error

    if not ObjectId.is_valid(user_id):
        raise credentials_error

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_error

    new_access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user.get("role", "user")}
    )

    return AccessTokenResponse(
        access_token=new_access_token,
        token_type="bearer",
    )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_error
    except JWTError:
        raise credentials_error

    if not ObjectId.is_valid(user_id):
        raise credentials_error

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_error

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        role=user.get("role", "user"),
    )


def get_current_admin(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


@app.get(
    "/me",
    response_model=UserResponse,
    tags=["Users"],
    summary="Get current user",
    description="Return the profile details of the currently authenticated user.",
)
async def read_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@app.patch(
    "/me",
    response_model=UserResponse,
    tags=["Users"],
    summary="Update current user",
    description="Update the full name of the currently authenticated user.",
)
async def update_me(
    updates: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
):
    update_data = {}

    if updates.full_name is not None:
        update_data["full_name"] = updates.full_name

    if not update_data:
        return current_user

    await users_collection.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_data},
    )

    user = await users_collection.find_one({"_id": ObjectId(current_user.id)})

    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        role=user.get("role", "user"),
    )


@app.post(
    "/documents/upload",
    response_model=DocumentResponse,
    tags=["Documents"],
    summary="Upload document",
    description="Upload a PDF, TXT, or DOCX file, store metadata in MongoDB, and index chunks in Qdrant.",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    extension = get_file_extension(file.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT, and DOCX files are allowed",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    extracted_text = extract_text_from_file(content, extension)
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract any text from the uploaded file",
        )

    s3_info = upload_file_to_s3(content, file.filename, file.content_type)
    file_url = s3_info["url"]
    size_bytes = s3_info["size"]
    s3_key = s3_info["key"]

    chunks = chunk_text(extracted_text)
    chunk_count = len([chunk for chunk in chunks if chunk.strip()])

    document_data = {
        "filename": file.filename,
        "file_type": extension.replace(".", ""),
        "owner_id": current_user.id,
        "size_bytes": size_bytes,
        "word_count": len(extracted_text.split()),
        "character_count": len(extracted_text),
        "chunk_count": chunk_count,
        "uploaded_at": datetime.now(timezone.utc),
        "file_url": file_url,
        "s3_key": s3_key,
    }

    result = await documents_collection.insert_one(document_data)

    store_document_chunks(
        document_id=str(result.inserted_id),
        owner_id=current_user.id,
        filename=file.filename,
        file_type=document_data["file_type"],
        chunks=chunks,
    )

    document_data["_id"] = result.inserted_id
    return build_document_response(document_data)


@app.get(
    "/documents",
    response_model=List[DocumentListResponse],
    tags=["Documents"],
    summary="List my documents",
    description="Return all documents uploaded by the current user. Optional filename filter is supported.",
)
async def list_my_documents(
    filename: Optional[str] = Query(
        default=None,
        min_length=1,
        description="Optional filename filter",
    ),
    current_user: UserResponse = Depends(get_current_user),
):
    documents: List[DocumentListResponse] = []

    query = {"owner_id": current_user.id}
    if filename:
        query["filename"] = {"$regex": filename, "$options": "i"}

    async for doc in documents_collection.find(query):
        documents.append(build_document_list_response(doc))

    return documents


@app.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    tags=["Documents"],
    summary="Get document",
    description="Return metadata for one uploaded document.",
)
async def get_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    obj_id = validate_object_id(document_id)

    document = await documents_collection.find_one(
        {"_id": obj_id, "owner_id": current_user.id}
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return build_document_response(document)


@app.get(
    "/documents/{document_id}/download",
    tags=["Documents"],
    summary="Download document",
    description="Stream the file directly from S3. Click 'Download file' in Swagger UI to save it.",
)
async def download_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    obj_id = validate_object_id(document_id)

    document = await documents_collection.find_one(
        {"_id": obj_id, "owner_id": current_user.id}
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    s3_key = document.get("s3_key")
    filename = document.get("filename", "downloaded_file")

    file_stream, content_type = get_file_stream_from_s3(s3_key)
    if file_stream is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve file from S3",
        )

    return StreamingResponse(
        file_stream,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@app.post(
    "/documents/search",
    response_model=List[DocumentSearchResult],
    tags=["Documents"],
    summary="Search document chunks",
    description="Search semantically across indexed document chunks in Qdrant.",
)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    results = search_document_chunks(
        query=request.query,
        owner_id=current_user.id,
        limit=request.limit,
    )
    return results


@app.delete(
    "/documents/{document_id}",
    tags=["Documents"],
    summary="Delete document",
    description="Delete a document, its stored file, and its Qdrant chunks.",
)
async def delete_document(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    obj_id = validate_object_id(document_id)

    document = await documents_collection.find_one(
        {"_id": obj_id, "owner_id": current_user.id}
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await documents_collection.delete_one(
        {"_id": obj_id, "owner_id": current_user.id}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_chunks(
        document_id=document_id,
        owner_id=current_user.id,
    )

    s3_key = document.get("s3_key")
    if s3_key:
        delete_file_from_s3(s3_key)

    return {"message": "Document deleted successfully"}


@app.get(
    "/users/",
    response_model=List[UserResponse],
    tags=["Admin"],
    summary="List users",
    description="Return all registered users. Admin only.",
)
async def list_users(current_user: UserResponse = Depends(get_current_admin)):
    users: List[UserResponse] = []

    async for u in users_collection.find():
        users.append(
            UserResponse(
                id=str(u["_id"]),
                email=u["email"],
                full_name=u.get("full_name"),
                role=u.get("role", "user"),
            )
        )

    return users