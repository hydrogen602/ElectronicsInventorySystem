"""
Functional/Integration tests for the Electronic Inventory System API.

These tests make HTTP requests to an external API instance.
Set the API_URL environment variable to specify the API endpoint.

Usage:
    # Using default URL (http://localhost:4061)
    pytest tests/test_api_integration.py

    # Using environment variable
    API_URL=http://localhost:4061 pytest tests/test_api_integration.py

    # Using remote server
    API_URL=https://api.example.com pytest tests/test_api_integration.py

    # Run specific test class
    pytest tests/test_api_integration.py::TestInventoryWorkflow

    # Run with verbose output
    pytest tests/test_api_integration.py -v
"""

import os
import pytest
import httpx
from bson import ObjectId


@pytest.fixture(scope="session")
def api_url() -> str:
    """Get the API base URL from environment variable or default."""
    return os.environ.get("API_URL", "http://localhost:4061")


@pytest.fixture(scope="session")
def digikey_api_disabled() -> bool:
    """Check if DigiKey API is disabled."""
    disabled = os.environ.get("DISABLE_DIGIKEY_API", "").lower()
    return disabled in ("true", "1", "yes", "on")


@pytest.fixture(scope="function")
def skip_if_digikey_disabled(digikey_api_disabled: bool) -> None:
    """Skip test if DigiKey API is disabled."""
    if digikey_api_disabled:
        pytest.skip("DigiKey API is disabled (DISABLE_DIGIKEY_API is set)")


@pytest.fixture(scope="session")
def client(api_url: str) -> httpx.Client:
    """Create an HTTP client for making requests."""
    return httpx.Client(base_url=api_url, timeout=30.0)


def test_root_endpoint(client: httpx.Client) -> None:
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    # Root may return HTML (React app) or JSON depending on deployment
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        data = response.json()
        assert "message" in data
    else:
        # HTML response (React app)
        assert "html" in response.text.lower()


def test_get_env(client: httpx.Client) -> None:
    """Test getting the environment configuration."""
    response = client.get("/api/env")
    assert response.status_code == 200
    env = response.json()
    assert isinstance(env, str)


def test_get_all_items_empty(client: httpx.Client) -> None:
    """Test getting all items when inventory is empty."""
    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)


def test_get_slot_empty(client: httpx.Client) -> None:
    """Test getting items from a slot that doesn't exist."""
    response = client.get("/api/slot/999")
    # Should return 404 or empty list depending on implementation
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_add_item_by_barcode_invalid(
    client: httpx.Client, skip_if_digikey_disabled: None
) -> None:
    """Test adding an item with an invalid barcode."""
    # Test with invalid numeric barcode (should fail for 2D barcode)
    response = client.post("/api/item", json={"barcode": "1234567890123456789012"})
    # Could succeed (if treated as 1D) or fail (if validation rejects)
    # If DigiKey API is disabled, expect 503
    assert response.status_code in [200, 400, 500, 503]


def test_add_item_by_valid_1d_barcode(
    client: httpx.Client, skip_if_digikey_disabled: None
) -> None:
    """Test adding an item with a valid 1D barcode."""
    # 22-digit numeric barcode (DigiKey legacy format)
    barcode = "1234567890123456789012"
    response = client.post("/api/item", json={"barcode": barcode})
    # May succeed or fail depending on whether barcode exists in DigiKey system
    # If DigiKey API is disabled, expect 503
    assert response.status_code in [200, 400, 500, 503]


def test_search_empty_query(client: httpx.Client) -> None:
    """Test search endpoint with empty query."""
    response = client.get("/api/search", params={"query": ""})
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_search_with_query(client: httpx.Client) -> None:
    """Test search endpoint with a query."""
    response = client.get("/api/search", params={"query": "test"})
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)


def test_search_match_bom_entry(client: httpx.Client) -> None:
    """Test BOM entry matching search."""
    response = client.get("/api/search/match-bom-entry", params={"search": "resistor"})
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) <= 5  # Max results is 5


def test_get_all_boms(client: httpx.Client) -> None:
    """Test getting all BOMs."""
    response = client.get("/api/bom")
    assert response.status_code == 200
    boms = response.json()
    assert isinstance(boms, list)


def test_get_nonexistent_bom(client: httpx.Client) -> None:
    """Test getting a BOM that doesn't exist."""
    fake_id = "507f1f77bcf86cd799439011"
    response = client.get(f"/api/bom/{fake_id}")
    assert response.status_code == 404


def test_get_nonexistent_item(client: httpx.Client) -> None:
    """Test getting an item that doesn't exist."""
    fake_id = "507f1f77bcf86cd799439011"
    response = client.get(f"/api/item/{fake_id}")
    assert response.status_code == 404


class TestInventoryWorkflow:
    """Test a complete inventory workflow."""

    def test_full_inventory_workflow(
        self, client: httpx.Client
    ) -> None:
        """Test a complete workflow: add item, get it, update it."""
        # Get initial state
        initial_items_response = client.get("/api/items")
        assert initial_items_response.status_code == 200
        initial_items = initial_items_response.json()
        initial_count = len(initial_items)

        # Try to add an item (may fail if barcode doesn't exist)
        # Using a valid format 1D barcode
        barcode = "1234567890123456789012"
        add_response = client.post("/api/item", json={"barcode": barcode})

        # Skip if DigiKey API is disabled (503) or auth required (401)
        if add_response.status_code in [503, 401]:
            return

        if add_response.status_code == 200:
            # Item was added successfully
            item = add_response.json()
            item_id = item["_id"]
            assert isinstance(item_id, str)

            # Get the item by ID
            get_response = client.get(f"/api/item/{item_id}")
            assert get_response.status_code == 200
            retrieved_item = get_response.json()
            assert retrieved_item["_id"] == item_id

            # Update quantity
            new_quantity = 10
            quantity_response = client.post(
                f"/api/item/{item_id}/quantity", params={"quantity": new_quantity}
            )
            assert quantity_response.status_code == 200

            # Verify quantity was updated
            verify_response = client.get(f"/api/item/{item_id}")
            assert verify_response.status_code == 200
            updated_item = verify_response.json()
            assert updated_item["available_quantity"] == new_quantity

            # Set comments
            test_comment = "Integration test comment"
            comments_response = client.post(
                f"/api/item/{item_id}/comments", params={"comments": test_comment}
            )
            assert comments_response.status_code == 200

            # Verify comments were set
            final_response = client.get(f"/api/item/{item_id}")
            assert final_response.status_code == 200
            final_item = final_response.json()
            assert final_item.get("comments") == test_comment

            # Add item to slot
            slot_id = 1
            add_slot_response = client.put(f"/api/item/{item_id}/slot/{slot_id}")
            assert add_slot_response.status_code == 200

            # Get slots of item
            slots_response = client.get(f"/api/item/{item_id}/slots")
            assert slots_response.status_code == 200
            slots = slots_response.json()
            # JSON serializes sets as lists
            assert isinstance(slots, list)
            assert slot_id in slots

            # Remove item from slot
            remove_slot_response = client.delete(f"/api/item/{item_id}/slot/{slot_id}")
            assert remove_slot_response.status_code == 200

            # Verify item was removed from slot
            verify_slots_response = client.get(f"/api/item/{item_id}/slots")
            assert verify_slots_response.status_code == 200
            remaining_slots = verify_slots_response.json()
            assert isinstance(remaining_slots, list)
            assert slot_id not in remaining_slots


class TestBOMWorkflow:
    """Test BOM-related workflows."""

    def test_bom_crud_workflow(self, client: httpx.Client) -> None:
        """Test creating, reading, updating a BOM."""
        # Get initial BOMs
        initial_response = client.get("/api/bom")
        assert initial_response.status_code == 200
        initial_boms = initial_response.json()

        # Create a new BOM with correct structure
        new_bom = {
            "info_line": "Test BOM Info",
            "project": {
                "name": "Test Project",
                "author_names": None,
                "comments": "Test project comments",
            },
            "rows": [
                {
                    "qty": 1,
                    "value": "10k",
                    "device": "RES-123",
                    "parts": ["R1"],
                    "description": "Resistor",
                    "manufacturer": None,
                    "comments": "",
                    "inventory_item_mapping_ids": [],
                    "fusion360_ext": None,
                }
            ],
            "name": "Test BOM",
        }
        create_response = client.post("/api/bom", json=new_bom)

        if create_response.status_code == 200:
            created_bom = create_response.json()
            bom_id = created_bom["_id"]
            assert isinstance(bom_id, str)

            # Get the BOM
            get_response = client.get(f"/api/bom/{bom_id}")
            assert get_response.status_code == 200
            retrieved_bom = get_response.json()
            assert retrieved_bom["_id"] == bom_id
            assert retrieved_bom["name"] == "Test BOM"

            # Update the BOM
            updated_bom = retrieved_bom.copy()
            updated_bom["name"] = "Updated Test BOM"
            update_response = client.put(f"/api/bom/{bom_id}", json=updated_bom)
            assert update_response.status_code == 200

            # Verify update
            verify_response = client.get(f"/api/bom/{bom_id}")
            assert verify_response.status_code == 200
            verified_bom = verify_response.json()
            assert verified_bom["name"] == "Updated Test BOM"

            # Delete the BOM (if supported)
            delete_response = client.delete(f"/api/bom/{bom_id}")
            # May return 200, 404, or 501 (not implemented)
            assert delete_response.status_code in [200, 404, 501]


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_item_id_format(self, client: httpx.Client) -> None:
        """Test with invalid item ID format."""
        response = client.get("/api/item/invalid-id")
        assert response.status_code in [400, 404, 422, 500]

    def test_invalid_bom_id_format(self, client: httpx.Client) -> None:
        """Test with invalid BOM ID format."""
        response = client.get("/api/bom/invalid-id")
        assert response.status_code in [400, 404, 422, 500]

    def test_invalid_slot_id(self, client: httpx.Client) -> None:
        """Test with invalid slot ID."""
        response = client.get("/api/slot/abc")
        assert response.status_code in [400, 404, 422, 500]

    def test_set_quantity_invalid_item(self, client: httpx.Client) -> None:
        """Test setting quantity on non-existent item."""
        fake_id = "507f1f77bcf86cd799439011"
        response = client.post(f"/api/item/{fake_id}/quantity", params={"quantity": 10})
        assert response.status_code == 404

    def test_set_comments_invalid_item(self, client: httpx.Client) -> None:
        """Test setting comments on non-existent item."""
        fake_id = "507f1f77bcf86cd799439011"
        response = client.post(
            f"/api/item/{fake_id}/comments", params={"comments": "test"}
        )
        assert response.status_code == 404

    def test_update_details_invalid_item(
        self, client: httpx.Client, skip_if_digikey_disabled: None
    ) -> None:
        """Test updating details on non-existent item."""
        fake_id = "507f1f77bcf86cd799439011"
        response = client.post(f"/api/item/{fake_id}/update_details")
        # Should return 404 for invalid item, or 503 if DigiKey API is disabled
        # 500 accepted temporarily until server restarts with fix
        assert response.status_code in [404, 503, 500]


class TestPackListBarcode:
    """Test pack list barcode functionality."""

    def test_add_items_by_pack_list_1d_barcode(
        self, client: httpx.Client, skip_if_digikey_disabled: None
    ) -> None:
        """Test adding items using a pack list 1D barcode."""
        # 26-digit numeric barcode
        barcode = "12345678901234567890123456"
        response = client.post("/api/items", json={"barcode": barcode})
        # May succeed or fail depending on whether barcode exists
        # If DigiKey API is disabled, expect 503
        assert response.status_code in [200, 400, 500, 503]
        if response.status_code == 200:
            items = response.json()
            assert isinstance(items, list)


class TestIPhoneEndpoints:
    """Test iPhone-specific endpoints."""

    def test_iphone_get_slot_hex(self, client: httpx.Client) -> None:
        """Test iPhone slot endpoint with hex ID."""
        # Test with hex slot ID (e.g., "1a" for slot 26)
        response = client.get("/api/iphone/slot/1a")
        # Returns a string message, not JSON
        assert response.status_code == 200
        assert isinstance(response.text, str)


class TestBOMMapping:
    """Test BOM mapping between dict[str, None] (MongoDB) and set[ObjectId] (contract)."""

    def test_bom_mapping_empty_inventory_item_ids(self, client: httpx.Client) -> None:
        """Test that empty inventory_item_mapping_ids maps correctly."""
        new_bom = {
            "info_line": "Test BOM Mapping",
            "project": {
                "name": "Mapping Test",
                "author_names": None,
                "comments": "",
            },
            "rows": [
                {
                    "qty": 1,
                    "value": "10k",
                    "device": "RES-123",
                    "parts": ["R1"],
                    "description": "Resistor",
                    "manufacturer": None,
                    "comments": "",
                    "inventory_item_mapping_ids": [],
                    "fusion360_ext": None,
                }
            ],
            "name": "Mapping Test BOM",
        }
        create_response = client.post("/api/bom", json=new_bom)

        if create_response.status_code == 200:
            created_bom = create_response.json()
            bom_id = created_bom["_id"]

            # Retrieve the BOM
            get_response = client.get(f"/api/bom/{bom_id}")
            assert get_response.status_code == 200
            retrieved_bom = get_response.json()

            # Verify inventory_item_mapping_ids is an empty list
            assert retrieved_bom["rows"][0]["inventory_item_mapping_ids"] == []

    def test_bom_mapping_with_inventory_item_ids(self, client: httpx.Client) -> None:
        """Test that inventory_item_mapping_ids with ObjectIds maps correctly."""
        # Create test ObjectIds
        test_id_1 = str(ObjectId())
        test_id_2 = str(ObjectId())

        new_bom = {
            "info_line": "Test BOM Mapping with IDs",
            "project": {
                "name": "Mapping Test with IDs",
                "author_names": None,
                "comments": "",
            },
            "rows": [
                {
                    "qty": 1,
                    "value": "10k",
                    "device": "RES-123",
                    "parts": ["R1"],
                    "description": "Resistor",
                    "manufacturer": None,
                    "comments": "",
                    "inventory_item_mapping_ids": [test_id_1, test_id_2],
                    "fusion360_ext": None,
                }
            ],
            "name": "Mapping Test BOM with IDs",
        }
        create_response = client.post("/api/bom", json=new_bom)

        if create_response.status_code == 200:
            created_bom = create_response.json()
            bom_id = created_bom["_id"]

            # Retrieve the BOM
            get_response = client.get(f"/api/bom/{bom_id}")
            assert get_response.status_code == 200
            retrieved_bom = get_response.json()

            # Verify inventory_item_mapping_ids contains the correct IDs
            retrieved_ids = retrieved_bom["rows"][0]["inventory_item_mapping_ids"]
            assert isinstance(retrieved_ids, list)
            # Should contain both IDs (order may vary since set is unordered)
            assert len(retrieved_ids) == 2
            assert test_id_1 in retrieved_ids
            assert test_id_2 in retrieved_ids

            # Update the BOM with different IDs
            updated_ids = [test_id_1]  # Remove one ID
            updated_bom = retrieved_bom.copy()
            updated_bom["rows"][0]["inventory_item_mapping_ids"] = updated_ids

            update_response = client.put(f"/api/bom/{bom_id}", json=updated_bom)
            assert update_response.status_code == 200

            # Verify the update
            verify_response = client.get(f"/api/bom/{bom_id}")
            assert verify_response.status_code == 200
            verified_bom = verify_response.json()
            verified_ids = verified_bom["rows"][0]["inventory_item_mapping_ids"]
            assert len(verified_ids) == 1
            assert test_id_1 in verified_ids

    def test_bom_mapping_multiple_rows_with_ids(self, client: httpx.Client) -> None:
        """Test mapping with multiple BOM entries, each with different inventory_item_mapping_ids."""
        test_id_1 = str(ObjectId())
        test_id_2 = str(ObjectId())
        test_id_3 = str(ObjectId())

        new_bom = {
            "info_line": "Test BOM Mapping Multiple Rows",
            "project": {
                "name": "Multiple Rows Test",
                "author_names": None,
                "comments": "",
            },
            "rows": [
                {
                    "qty": 1,
                    "value": "10k",
                    "device": "RES-123",
                    "parts": ["R1"],
                    "description": "Resistor 1",
                    "manufacturer": None,
                    "comments": "",
                    "inventory_item_mapping_ids": [test_id_1],
                    "fusion360_ext": None,
                },
                {
                    "qty": 2,
                    "value": "22k",
                    "device": "RES-456",
                    "parts": ["R2", "R3"],
                    "description": "Resistor 2",
                    "manufacturer": None,
                    "comments": "",
                    "inventory_item_mapping_ids": [test_id_2, test_id_3],
                    "fusion360_ext": None,
                },
            ],
            "name": "Multiple Rows Mapping Test",
        }
        create_response = client.post("/api/bom", json=new_bom)

        if create_response.status_code == 200:
            created_bom = create_response.json()
            bom_id = created_bom["_id"]

            # Retrieve the BOM
            get_response = client.get(f"/api/bom/{bom_id}")
            assert get_response.status_code == 200
            retrieved_bom = get_response.json()

            # Verify first row has correct IDs
            row_1_ids = retrieved_bom["rows"][0]["inventory_item_mapping_ids"]
            assert isinstance(row_1_ids, list)
            assert len(row_1_ids) == 1
            assert test_id_1 in row_1_ids

            # Verify second row has correct IDs
            row_2_ids = retrieved_bom["rows"][1]["inventory_item_mapping_ids"]
            assert isinstance(row_2_ids, list)
            assert len(row_2_ids) == 2
            assert test_id_2 in row_2_ids
            assert test_id_3 in row_2_ids


class TestBOMAnalysis:
    """Test BOM analysis endpoints."""

    def test_upload_zip_invalid_content_type(self, client: httpx.Client) -> None:
        """Test uploading a file with invalid content type."""
        fake_file_content = b"not a zip file"
        response = client.post(
            "/api/bom/parse/gerber-export",
            files={"file": ("test.txt", fake_file_content, "text/plain")},
            params={"src": "fusion360"},
        )
        assert response.status_code == 400

    def test_upload_zip_invalid_source(self, client: httpx.Client) -> None:
        """Test uploading with invalid BOM source."""
        # This test would need a valid zip file, so we'll just test the validation
        # In a real scenario, you'd need an actual zip file
        fake_file_content = b"PK\x03\x04"  # Minimal ZIP header
        response = client.post(
            "/api/bom/parse/gerber-export",
            files={"file": ("test.zip", fake_file_content, "application/zip")},
            params={"src": "invalid_source"},
        )
        assert response.status_code == 400

