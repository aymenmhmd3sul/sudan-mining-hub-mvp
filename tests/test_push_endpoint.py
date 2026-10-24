import pytest

from app.services.push_endpoint import is_safe_push_endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://push.example.invalid/subscription",
        "https://push.example.test:443/path",
        "https://push.example.test/path?token=abc",
    ],
)
def test_safe_push_endpoints_are_accepted(endpoint):
    assert is_safe_push_endpoint(endpoint)


@pytest.mark.parametrize(
    "endpoint",
    [
        "",
        "http://push.example.test/subscription",
        "https://localhost/subscription",
        "https://service.localhost/subscription",
        "https://printer.local/subscription",
        "https://service.internal/subscription",
        "https://127.0.0.1/subscription",
        "https://10.0.0.1/subscription",
        "https://192.168.1.10/subscription",
        "https://169.254.1.1/subscription",
        "https://192.0.2.1/subscription",
        "https://[::1]/subscription",
        "https://user:pass@push.example.test/subscription",
        "https://push.example.test:8443/subscription",
        "https://push.example.test:notaport/subscription",
        "https:///subscription",
        "https://singlelabel/subscription",
        "https://push.example.test/subscription#fragment",
        "https://push.example.test/bad path",
    ],
)
def test_unsafe_push_endpoints_are_rejected(endpoint):
    assert not is_safe_push_endpoint(endpoint)
