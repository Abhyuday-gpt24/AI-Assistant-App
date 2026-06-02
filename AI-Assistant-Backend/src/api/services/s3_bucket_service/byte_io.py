"""Byte-level helpers used by the ingestion pipeline: download source docs, and
write converted Markdown + extracted images back to S3.
"""

from botocore.exceptions import ClientError
from config import settings
from src.api.exceptions import AppException, NotFoundError

from src.api.services.s3_bucket_service.paths import build_public_url


def download_bytes(storage_path, s3):
    """Fetch an object's raw bytes (+ its content type)."""
    try:
        resp = s3.get_object(Bucket=settings.SUPABASE_BUCKET, Key=storage_path)
        return resp["Body"].read(), resp.get("ContentType")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
            raise NotFoundError(detail=f"File not found: {storage_path}")
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")


def upload_bytes(key, data, content_type, s3):
    """Write raw bytes to S3 and return the object's public URL."""
    try:
        s3.put_object(
            Bucket=settings.SUPABASE_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return build_public_url(key)
    except ClientError as e:
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")
