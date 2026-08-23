import os
import uuid
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "uploads")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def upload_file_to_s3(content: bytes, filename: str, content_type: str) -> dict:
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
    s3_key = f"{S3_PREFIX}/{unique_name}"

    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )

    url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
    return {"key": s3_key, "url": url, "size": len(content)}


def get_file_stream_from_s3(s3_key: str):
    """Fetches the file body stream and content type directly from S3."""
    if not s3_key:
        return None, None
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        content_type = response.get("ContentType", "application/octet-stream")
        return response["Body"], content_type
    except ClientError:
        return None, None


def delete_file_from_s3(s3_key: str) -> None:
    if not s3_key:
        return
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
    except ClientError:
        pass


def get_presigned_download_url(s3_key: str, expires_in: int = 3600) -> str:
    if not s3_key:
        return ""
    try:
        return s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires_in,
        )
    except ClientError:
        return ""