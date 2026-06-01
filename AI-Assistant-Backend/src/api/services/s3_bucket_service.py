from botocore.exceptions import ClientError
from config import settings
from src.api.exceptions import AppException, NotFoundError
import uuid


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_files(files):
    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            raise AppException(status_code=415, detail=f"Unsupported file type: {file.content_type}")
        if file.size and file.size > MAX_FILE_SIZE:
            raise AppException(status_code=413, detail=f"File too large: {file.filename}")


async def upload_files_to_s3(files, folder, s3):
    validate_files(files)

    results, errors = [], []

    for file in files:
        try:
            ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
            unique_name = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
            storage_path = f"{folder}/{unique_name}" if folder else unique_name

            file_bytes = await file.read()

            s3.put_object(
                Bucket=settings.SUPABASE_BUCKET,
                Key=storage_path,
                Body=file_bytes,
                ContentType=file.content_type or "application/octet-stream",
            )

            public_url = f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{storage_path}"

            results.append({
                "filename": file.filename,
                "storage_path": storage_path,
                "public_url": public_url,
                "size_bytes": len(file_bytes),
                "status": "success",
            })
        except ClientError as e:
            errors.append({
                "filename": file.filename,
                "error": e.response["Error"]["Message"],
                "status": "failed",
            })
        except Exception as e:
            errors.append({"filename": file.filename, "error": str(e), "status": "failed"})

    return {"uploaded": results, "failed": errors, "total": len(files), "successful": len(results)}


def list_files_from_s3(folder, limit, offset, s3):
    try:
        kwargs = {"Bucket": settings.SUPABASE_BUCKET, "MaxKeys": limit}
        if folder:
            kwargs["Prefix"] = f"{folder}/"

        response = s3.list_objects_v2(**kwargs)
        all_objects = response.get("Contents", [])
        paginated = all_objects[offset: offset + limit]

        files = []
        for obj in paginated:
            key = obj["Key"]
            files.append({
                "name": key.split("/")[-1],
                "storage_path": key,
                "size": obj.get("Size"),
                "last_modified": obj["LastModified"].isoformat(),
                "public_url": f"{settings.SUPABASE_S3_ENDPOINT}/{settings.SUPABASE_BUCKET}/{key}",
            })

        return {"files": files, "total": len(files)}

    except ClientError as e:
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")


def delete_file_from_s3(file_path, s3):
    try:
        s3.head_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            raise NotFoundError(detail=f"File not found: {file_path}")
        raise AppException(status_code=502, detail=f"S3 error: {e.response['Error']['Message']}")

    s3.delete_object(Bucket=settings.SUPABASE_BUCKET, Key=file_path)
    return {"message": "File deleted successfully", "file_path": file_path}