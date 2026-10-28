import io

import boto3
import pytest
from azure.core.exceptions import ClientAuthenticationError, ResourceExistsError
from azure.storage.blob import ContentSettings
from botocore.config import Config
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.frontend import register_frontend
from app.api.security_headers import register_security_headers
from app.core.config import Settings
from app.integrations.supabase_storage import SupabaseEvidenceContainer


def _container():
    container = object.__new__(SupabaseEvidenceContainer)
    container.bucket = "evidence"
    container.client = boto3.client(
        "s3", region_name="us-east-1", aws_access_key_id="test",
        aws_secret_access_key="test", endpoint_url="https://storage.example.test",
        config=Config(signature_version="s3v4"),
    )
    return container


def test_private_evidence_upload_download_and_compensation():
    container = _container()
    key = "company/unique.pdf"
    data = b"%PDF-test"
    raw_stream = io.BytesIO(data)
    stream = StreamingBody(raw_stream, len(data))
    with Stubber(container.client) as stub:
        stub.add_client_error("head_object", service_error_code="404", http_status_code=404,
                              expected_params={"Bucket": "evidence", "Key": key})
        stub.add_response("put_object", {}, {
            "Bucket": "evidence", "Key": key, "Body": data,
            "ContentType": "application/pdf", "CacheControl": "private, no-store",
        })
        stub.add_response("get_object", {"Body": stream}, {"Bucket": "evidence", "Key": key})
        stub.add_response("delete_object", {}, {"Bucket": "evidence", "Key": key})
        container.upload_blob(name=key, data=data, content_settings=ContentSettings(content_type="application/pdf"))
        assert b"".join(container.download_blob(key).chunks()) == data
        assert raw_stream.closed
        container.delete_blob(key)
        stub.assert_no_pending_responses()


def test_existing_evidence_is_not_overwritten():
    container = _container()
    with Stubber(container.client) as stub:
        stub.add_response("head_object", {}, {"Bucket": "evidence", "Key": "existing"})
        with pytest.raises(ResourceExistsError):
            container.upload_blob(name="existing", data=b"replacement")
        stub.assert_no_pending_responses()


def test_storage_auth_error_does_not_expose_provider_message():
    container = _container()
    with Stubber(container.client) as stub:
        stub.add_client_error("head_bucket", service_error_code="SignatureDoesNotMatch",
                              service_message="sensitive provider detail", http_status_code=403)
        with pytest.raises(ClientAuthenticationError) as error:
            container.get_container_properties()
        assert "sensitive" not in str(error.value)


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://", "postgresql+psycopg://"])
def test_supabase_database_url_uses_installed_driver(prefix):
    settings = Settings(database_url=prefix + "user:encoded%40password@host:5432/postgres?sslmode=require")
    assert settings.database_url == "postgresql+psycopg://user:encoded%40password@host:5432/postgres?sslmode=require"


def test_supabase_configuration_fails_closed():
    with pytest.raises(ValueError, match="Supabase requires"):
        Settings(evidence_backend="supabase")


def test_frontend_fallback_preserves_api_and_static_404s(tmp_path):
    (tmp_path / "index.html").write_text("<html>Nexora</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "shell.js").write_text("export const app = true")
    app = FastAPI()
    register_security_headers(app)

    @app.get("/api/example")
    def example():
        return {"ok": True}

    register_frontend(app, str(tmp_path))
    with TestClient(app) as client:
        for path in ("/", "/proyectos", "/verificar/comprobante/token"):
            response = client.get(path)
            assert response.status_code == 200
            assert "Nexora" in response.text
            assert response.headers["cache-control"] == "no-store"
            assert "script-src 'self'" in response.headers["content-security-policy"]
        for path in ("/api/missing", "/assets/missing.js", "/missing.js", "/../requirements.txt"):
            assert client.get(path).status_code == 404
        assert client.get("/api/example").json() == {"ok": True}
        assert client.get("/api/example").headers["content-security-policy"].startswith("default-src 'none'")
        assert "immutable" in client.get("/assets/shell.js").headers["cache-control"]
        assert client.head("/proyectos").status_code == 200


def test_frontend_requires_real_build(tmp_path):
    with pytest.raises(RuntimeError, match="built index.html"):
        register_frontend(FastAPI(), str(tmp_path))
