from starlette.requests import Request

from app.api.deps import _client_ip


def _request(*, forwarded_for: str | None, client_host: str = "10.0.0.4") -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/auth/login",
            "raw_path": b"/api/auth/login",
            "query_string": b"",
            "headers": headers,
            "client": (client_host, 443),
            "server": ("nexora.example", 443),
        }
    )


def test_client_ip_uses_rightmost_azure_appended_value():
    request = _request(forwarded_for="203.0.113.8, 198.51.100.27")
    assert _client_ip(request) == "198.51.100.27"


def test_client_ip_ignores_empty_forwarded_values():
    request = _request(forwarded_for=" , 198.51.100.27, ")
    assert _client_ip(request) == "198.51.100.27"


def test_client_ip_falls_back_to_socket_peer_without_forwarded_header():
    request = _request(forwarded_for=None, client_host="127.0.0.1")
    assert _client_ip(request) == "127.0.0.1"
