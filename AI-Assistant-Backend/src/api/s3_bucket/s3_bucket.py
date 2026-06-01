import boto3
from config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.SUPABASE_S3_ENDPOINT,
        aws_access_key_id=settings.SUPABASE_ACCESS_KEY_ID,
        aws_secret_access_key=settings.SUPABASE_SECRET_ACCESS_KEY,
        region_name=settings.SUPABASE_REGION,
    )