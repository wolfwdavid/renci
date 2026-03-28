"""Google Cloud Storage client for photo/asset uploads."""

from google.cloud import storage
from config import settings


def get_storage_client():
    return storage.Client(project=settings.gcp_project_id)


async def upload_photo(business_slug: str, file_data: bytes, filename: str) -> str:
    """Upload a photo to GCS and return the public URL."""
    client = get_storage_client()
    bucket = client.bucket(settings.gcs_bucket)
    blob = bucket.blob(f"{business_slug}/{filename}")
    blob.upload_from_string(file_data, content_type="image/jpeg")
    blob.make_public()
    return blob.public_url
