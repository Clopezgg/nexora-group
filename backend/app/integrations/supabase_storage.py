"""Supabase private S3 storage using the existing evidence container contract.

S3 credentials remain server-side; all reads still pass through NEXORA RBAC.
Azure exception types bridge the existing classified storage error handlers.
"""

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings


def _call(operation, **kwargs):
    try:
        return operation(**kwargs)
    except ClientError as exc:
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 503)
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"InvalidAccessKeyId", "SignatureDoesNotMatch", "ExpiredToken"} or status == 401:
            raise ClientAuthenticationError("Storage authentication failed") from exc
        if status == 404:
            raise ResourceNotFoundError("Storage object not found") from exc
        error = HttpResponseError(message="Storage request failed")
        error.status_code = status
        raise error from exc
    except BotoCoreError as exc:
        raise ServiceRequestError("Storage connection failed") from exc


class _Download:
    def __init__(self, body):
        self.body = body

    def chunks(self):
        try:
            yield from self.body.iter_chunks(chunk_size=64 * 1024)
        finally:
            self.body.close()


class SupabaseEvidenceContainer:
    def __init__(self, settings: Settings):
        import boto3
        from botocore.config import Config

        self.bucket = settings.evidence_container_name
        self.client = boto3.client(
            "s3", endpoint_url=settings.supabase_s3_endpoint.rstrip("/"),
            region_name=settings.supabase_s3_region,
            aws_access_key_id=settings.supabase_s3_access_key_id,
            aws_secret_access_key=settings.supabase_s3_secret_access_key,
            config=Config(
                signature_version="s3v4", s3={"addressing_style": "path"},
                connect_timeout=5, read_timeout=30,
                retries={"max_attempts": 1, "mode": "standard"},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        )

    def get_container_properties(self):
        return _call(self.client.head_bucket, Bucket=self.bucket)

    def upload_blob(self, *, name, data, overwrite=False, content_settings=None):
        # Evidence keys include a freshly generated UUID. Reuse of an existing
        # key is rejected; bucket creation/policy changes are never automatic.
        if not overwrite:
            try:
                _call(self.client.head_object, Bucket=self.bucket, Key=name)
            except ResourceNotFoundError:
                pass
            else:
                raise ResourceExistsError("Evidence already exists")
        return _call(
            self.client.put_object, Bucket=self.bucket, Key=name, Body=data,
            ContentType=getattr(content_settings, "content_type", None) or "application/octet-stream",
            CacheControl="private, no-store",
        )

    def download_blob(self, name):
        result = _call(self.client.get_object, Bucket=self.bucket, Key=name)
        return _Download(result["Body"])

    def delete_blob(self, name):
        return _call(self.client.delete_object, Bucket=self.bucket, Key=name)
