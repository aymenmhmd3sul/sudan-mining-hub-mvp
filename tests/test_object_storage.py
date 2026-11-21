from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import object_storage as storage


@pytest.fixture
def s3_settings(monkeypatch):
    values = {
        "LISTING_STORAGE_BACKEND": "s3",
        "AWS_ACCESS_KEY_ID": "test-access",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "AWS_ENDPOINT_URL_S3": (
            "https://storage.example"
        ),
        "AWS_REGION": "eu-central-1",
        "NEON_STORAGE_BUCKET": "listing-images",
    }
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


def test_s3_upload_uses_listing_key_and_metadata(
    monkeypatch, s3_settings
):
    calls = []

    class FakeClient:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        storage,
        "_s3_client",
        lambda: FakeClient(),
    )

    result = storage.store_listing_image(
        77,
        "77-example.png",
        b"image-data",
        "image/png",
    )

    assert result == "listings/77/77-example.png"
    assert calls == [{
        "Bucket": "listing-images",
        "Key": "listings/77/77-example.png",
        "Body": b"image-data",
        "ContentType": "image/png",
        "CacheControl": "public, max-age=31536000, immutable",
    }]


def test_s3_configuration_rejects_missing_values(
    monkeypatch, s3_settings
):
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", None)

    with pytest.raises(RuntimeError, match="AWS_SECRET_ACCESS_KEY"):
        storage._s3_configuration()


def test_storage_key_resolves_to_public_url(
    monkeypatch, s3_settings
):
    assert storage.resolve_media_url(
        "listings/77/example image.png"
    ) == (
        "https://storage.example/listing-images/"
        "listings/77/example%20image.png"
    )


@pytest.mark.parametrize(
    "legacy_url",
    [
        "/uploads/listings/old-image.png",
        "https://old-storage.example/old-image.png",
        "http://old-storage.example/old-image.png",
    ],
)
def test_legacy_urls_remain_unchanged(legacy_url):
    assert storage.resolve_media_url(legacy_url) == legacy_url


def test_s3_delete_uses_listing_object_key(
    monkeypatch, s3_settings
):
    calls = []

    class FakeClient:
        def delete_object(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        storage,
        "_s3_client",
        lambda: FakeClient(),
    )

    storage.delete_stored_image(
        "listings/77/77-example.png"
    )

    assert calls == [{
        "Bucket": "listing-images",
        "Key": "listings/77/77-example.png",
    }]


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "../other-bucket/object",
        "users/77/avatar.png",
        "listings/77/../../secret",
        "/listings/77/image.png",
    ],
)
def test_s3_delete_rejects_keys_outside_listing_scope(
    monkeypatch, s3_settings, unsafe_key
):
    calls = []

    class FakeClient:
        def delete_object(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        storage,
        "_s3_client",
        lambda: FakeClient(),
    )

    with pytest.raises(RuntimeError):
        storage.delete_stored_image(unsafe_key)

    assert calls == []
