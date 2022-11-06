from hashlib import sha224

from openprocurement.api.context import set_now
from openprocurement.api.tests.base import singleton_app, app, change_auth
from openprocurement.api.mask import mask_object_data
from unittest.mock import patch, MagicMock
from copy import deepcopy
import json


@patch("openprocurement.api.mask.MASK_OBJECT_DATA", True)
@patch("openprocurement.api.mask.MASK_IDENTIFIER_IDS", [
    sha224("00000000".encode()).hexdigest(),
])
def test_mask_function():
    with open("src/openprocurement/tender/core/tests/data/tender_to_mask.json") as f:
        data = json.load(f)
    initial_data = deepcopy(data)

    request = MagicMock()
    mask_object_data(request, data)

    assert data["title"] == "Тимчасово замасковано, щоб русня не підглядала"
    assert data["_id"] == initial_data["_id"]


@patch("openprocurement.api.mask.MASK_OBJECT_DATA", True)
@patch("openprocurement.api.mask.MASK_IDENTIFIER_IDS", [
    sha224("00000000".encode()).hexdigest(),
])
def test_mask_tender_by_identifier(app):
    set_now()
    with open(f"src/openprocurement/tender/core/tests/data/tender_to_mask.json") as f:
        data = json.load(f)
    app.app.registry.mongodb.tenders.save(data, insert=True)

    id = data['_id']

    response = app.get(f"/tenders/{id}")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["title"] == "Тимчасово замасковано, щоб русня не підглядала"

@patch("openprocurement.api.mask.MASK_OBJECT_DATA", True)
@patch("openprocurement.api.mask.MASK_IDENTIFIER_IDS", [])
def test_mask_tender_by_is_masked(app):
    set_now()
    with open(f"src/openprocurement/tender/core/tests/data/tender_to_mask.json") as f:
        data = json.load(f)
    data["is_masked"] = True
    app.app.registry.mongodb.tenders.save(data, insert=True)

    id = data['_id']

    # Check tender masked
    response = app.get(f"/tenders/{id}")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["title"] == "Тимчасово замасковано, щоб русня не підглядала"
    assert data["items"][0]["description"] ==  "0" * len(data["items"][0]["description"])

    # Check field is hidden
    assert "is_masked" not in response.json["data"]

    # Patch tender as excluded from masking role
    with change_auth(app, ("Basic", ("administrator", ""))):
        response = app.patch_json(f"/tenders/{id}", {"data": {"description": "test"}})
    assert response.status_code == 200
    data = response.json["data"]
    assert data["description"] == "test"
    assert data["items"][0]["description"] !=  "0" * len(data["items"][0]["description"])

    # Check field is hidden
    assert "is_masked" not in response.json["data"]

    # Check that after modification tender is still masked
    response = app.get(f"/tenders/{id}")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["title"] == "Тимчасово замасковано, щоб русня не підглядала"
    assert data["items"][0]["description"] ==  "0" * len(data["items"][0]["description"])

@patch("openprocurement.api.mask.MASK_OBJECT_DATA", True)
@patch("openprocurement.api.mask.MASK_IDENTIFIER_IDS", [])
def test_mask_tender_skipped(app):
    set_now()
    with open(f"src/openprocurement/tender/core/tests/data/tender_to_mask.json") as f:
        data = json.load(f)
    app.app.registry.mongodb.tenders.save(data, insert=True)

    id = data['_id']

    response = app.get(f"/tenders/{id}")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["title"] != "Тимчасово замасковано, щоб русня не підглядала"

