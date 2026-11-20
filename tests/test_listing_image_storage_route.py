import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile

from app.models.listing import Listing
from app.models.listing_media import ListingMedia
from app.routers import marketplace


PNG = b"\x89PNG\r\n\x1a\nSMH-ROUTE-TEST"


class FakeQuery:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result

    def count(self):
        return 0


class FakeDB:
    def __init__(self, fail_commit=False):
        self.fail_commit = fail_commit
        self.added = []
        self.committed = False
        self.rolled_back = False
        self.listing = SimpleNamespace(id=77, owner_id=12)

    def query(self, model):
        if model is Listing:
            return FakeQuery(self.listing)
        if model is ListingMedia:
            return FakeQuery()
        raise AssertionError(f"Unexpected query model: {model}")

    def add(self, item):
        self.added.append(item)

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("simulated commit failure")
        self.committed = True

    def refresh(self, item):
        item.id = 321

    def rollback(self):
        self.rolled_back = True


def make_upload():
    return UploadFile(
        file=BytesIO(PNG),
        filename="test.png",
        headers=Headers({"content-type": "image/png"}),
    )


def make_listing():
    return SimpleNamespace(id=77, owner_id=12)


def make_user():
    return SimpleNamespace(id=12, role="MERCHANT")


def invoke(db):
    return asyncio.run(
        marketplace.upload_listing_image(
            listing_id=77,
            file=make_upload(),
            db=db,
            user=make_user(),
            _subscription_user=make_user(),
        )
    )


def test_upload_route_success(monkeypatch):
    stored = []
    db = FakeDB()

    def store(*args):
        stored.append(args)
        return "listings/77/test.png"

    monkeypatch.setattr(marketplace, "store_listing_image", store)
    monkeypatch.setattr(
        marketplace,
        "resolve_media_url",
        lambda value: "https://storage.example/" + value,
    )

    result = invoke(db)

    assert db.committed
    assert not db.rolled_back
    assert len(db.added) == 1
    assert result["id"] == 321
    assert result["url"] == "https://storage.example/listings/77/test.png"
    assert stored[0][0] == 77
    assert stored[0][2] == PNG


def test_upload_route_cleans_storage_when_url_resolution_fails(monkeypatch):
    deleted = []
    db = FakeDB()

    monkeypatch.setattr(
        marketplace,
        "store_listing_image",
        lambda *args: "listings/77/test.png",
    )
    monkeypatch.setattr(
        marketplace,
        "resolve_media_url",
        lambda value: (_ for _ in ()).throw(RuntimeError("URL failure")),
    )
    monkeypatch.setattr(
        marketplace,
        "delete_stored_image",
        lambda value: deleted.append(value),
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        invoke(db)

    assert exc.value.status_code == 503
    assert deleted == ["listings/77/test.png"]
    assert not db.committed
    assert not db.added


def test_upload_route_rolls_back_and_cleans_storage_on_commit_failure(monkeypatch):
    deleted = []
    db = FakeDB(fail_commit=True)

    monkeypatch.setattr(
        marketplace,
        "store_listing_image",
        lambda *args: "listings/77/test.png",
    )
    monkeypatch.setattr(
        marketplace,
        "resolve_media_url",
        lambda value: "https://storage.example/" + value,
    )
    monkeypatch.setattr(
        marketplace,
        "delete_stored_image",
        lambda value: deleted.append(value),
    )

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        invoke(db)

    assert exc.value.status_code == 500
    assert db.rolled_back
    assert deleted == ["listings/77/test.png"]
    assert len(db.added) == 1
