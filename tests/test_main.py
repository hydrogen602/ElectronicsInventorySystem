from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx
import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from typing import AsyncGenerator, Generator

from electronic_inv_sys.infrastructure.db.in_memory import (
    InMemoryBomRepository,
    InMemoryRepository,
)
from electronic_inv_sys.infrastructure.env_config import EnvConfig
from electronic_inv_sys.infrastructure.metadata_store import MetadataFileStore
from electronic_inv_sys.main import app
from electronic_inv_sys.contracts.models import ExistingInventoryItem
from electronic_inv_sys.web_api.api_models import AddItemByBarcodeRequest
from electronic_inv_sys.services import Services, ServicesProviderSingleton
from electronic_inv_sys.util import Environment
from electronic_inv_sys.logic.bom import BomAnalysis

from tests.mocks import DigiKeyAPIImplModified


@asynccontextmanager
async def mock_services() -> AsyncGenerator[Services, None]:
    d = {
        ObjectId("123456789012345678901234"): ExistingInventoryItem(
            _id=ObjectId("123456789012345678901234"),
            available_quantity=5,
            item_description="Test item",
            digikey_part_number="TEST123",
            slot_ids={1},
            comments="",
            product_details=None,
            is_description_placeholder=False,
            digikey_orders=[],
            digikey_barcode_2d=set(),
            digikey_barcode_1d=set(),
            manufacturer_name=None,
            manufacturer_part_number=None,
        )
    }

    async with httpx.AsyncClient() as session:
        metadata = MetadataFileStore(path=".env.test.json")
        config = EnvConfig(dotenv_path=".env.test", env=Environment.TEST)

        inventory = InMemoryRepository(d)
        services = Services(
            inventory=inventory,
            config=config,
            metadata=metadata,
            digikey_api=DigiKeyAPIImplModified(session, metadata, config),
            bom_analysis=BomAnalysis(inventory),
            bom=InMemoryBomRepository({}),
        )
        yield services


@asynccontextmanager
async def mock_service_lifespan(app: FastAPI):
    async with mock_services() as s:
        ServicesProviderSingleton(s)
        yield
        ServicesProviderSingleton.delete_instance()


@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    app.router.lifespan_context = mock_service_lifespan
    with TestClient(app) as client:
        yield client


def test_index(test_client: TestClient):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World!"}


def test_get_inventory(test_client: TestClient):
    response = test_client.get("/api/slot/1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_add_item_by_barcode(test_client: TestClient):
    request_data = AddItemByBarcodeRequest(barcode="1234567890123456789012")
    response = test_client.post("/api/item", json=request_data.model_dump())
    assert response.status_code in [200, 400, 500]


def test_get_all_items(test_client: TestClient):
    response = test_client.get("/api/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_item(test_client: TestClient):
    response = test_client.get("/api/item/123456789012345678901234")
    assert response.status_code == 200
    assert response.json()["_id"] == "123456789012345678901234"


def test_update_item_details(test_client: TestClient):
    response = test_client.post("/api/item/123456789012345678901234/update_details")
    assert response.status_code in [200, 500]


def test_update_all_items_details(test_client: TestClient):
    response = test_client.post("/api/items/update_details")
    assert response.status_code in [200, 500]


def test_set_comments(test_client: TestClient):
    response = test_client.post(
        "/api/item/123456789012345678901234/comments?comments=This%20is%20a%20test%20comment",
    )
    # assert response.text == "This is a test comment"
    assert response.status_code == 200


def test_set_quantity(test_client: TestClient):
    response = test_client.post(
        "/api/item/123456789012345678901234/quantity?quantity=50"
    )
    assert response.status_code == 200
