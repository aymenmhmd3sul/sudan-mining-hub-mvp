from pathlib import Path
from urllib.parse import quote

from app.core.config import settings


def _backend() -> str:
    backend = settings.LISTING_STORAGE_BACKEND.strip().lower()
    if backend not in {"local", "s3"}:
        raise RuntimeError("Unsupported listing storage backend")
    return backend


def _s3_configuration():
    required = {
        "AWS_ACCESS_KEY_ID": settings.AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": settings.AWS_SECRET_ACCESS_KEY,
        "AWS_ENDPOINT_URL_S3": settings.AWS_ENDPOINT_URL_S3,
        "AWS_REGION": settings.AWS_REGION,
        "NEON_STORAGE_BUCKET": settings.NEON_STORAGE_BUCKET,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing object storage configuration: " + ", ".join(missing)
        )
    return required


def _s3_client():
    import boto3
    from botocore.config import Config

    config = _s3_configuration()
    return boto3.client(
        "s3",
        endpoint_url=config["AWS_ENDPOINT_URL_S3"],
        aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"],
        region_name=config["AWS_REGION"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def store_listing_image(
    listing_id: int,
    filename: str,
    data: bytes,
    content_type: str,
) -> str:
    if _backend() == "s3":
        config = _s3_configuration()
        key = f"listings/{listing_id}/{filename}"

        _s3_client().put_object(
            Bucket=config["NEON_STORAGE_BUCKET"],
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        return key

    upload_dir = Path("app/static/uploads/listings")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / filename
    target.write_bytes(data)
    return f"/uploads/listings/{filename}"


def resolve_media_url(value: str) -> str:
    if value.startswith("/") or value.startswith("https://") or value.startswith("http://"):
        return value

    if _backend() != "s3":
        raise RuntimeError(
            "An object storage key exists but S3 storage is not configured"
        )

    config = _s3_configuration()
    endpoint = config["AWS_ENDPOINT_URL_S3"].rstrip("/")
    bucket = quote(config["NEON_STORAGE_BUCKET"], safe="")
    key = quote(value.lstrip("/"), safe="/")
    return f"{endpoint}/{bucket}/{key}"


def delete_stored_image(value: str) -> None:
    if value.startswith("/uploads/listings/"):
        relative_name = value.removeprefix("/uploads/listings/")
        if Path(relative_name).name != relative_name:
            raise RuntimeError("Invalid local image path")

        target = Path("app/static/uploads/listings") / relative_name
        target.unlink(missing_ok=True)
        return

    if value.startswith("http://") or value.startswith("https://"):
        return

    if _backend() == "s3":
        parts = value.split("/")

        if (
            len(parts) != 3
            or parts[0] != "listings"
            or not parts[1].isdigit()
            or not parts[2]
            or parts[2] in {".", ".."}
            or "/" in parts[2]
            or "\\" in parts[2]
            or not parts[2].startswith(parts[1] + "-")
        ):
            raise RuntimeError("Invalid listing image storage key")

        config = _s3_configuration()
        _s3_client().delete_object(
            Bucket=config["NEON_STORAGE_BUCKET"],
            Key=value,
        )
