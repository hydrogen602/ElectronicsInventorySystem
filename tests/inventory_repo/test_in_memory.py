from bson import ObjectId
from pydantic import ValidationError
import pytest

from electronic_inv_sys.contracts.models import (
    DigiKeyProductDetails,
    ExistingInventoryItem,
    NewInventoryItem,
)
from electronic_inv_sys.contracts.repos import (
    DuplicateDigiKeyPartNumberError,
    InventoryRepository,
)
from electronic_inv_sys.infrastructure.db.in_memory import InMemoryRepository


def existing_inv_item(
    _id: ObjectId,
    available_quantity: int,
    item_description: str,
    digikey_part_number: str | None,
) -> ExistingInventoryItem:
    return ExistingInventoryItem(
        _id=_id,
        available_quantity=available_quantity,
        item_description=item_description,
        digikey_part_number=digikey_part_number,
        slot_ids=set(),
        comments="",
        product_details=None,
        is_description_placeholder=False,
        digikey_orders=[],
        digikey_barcode_2d=set(),
        digikey_barcode_1d=set(),
        manufacturer_name=None,
        manufacturer_part_number=None,
    )


def new_inv_item(
    available_quantity: int,
    item_description: str,
    digikey_part_number: str | None,
    product_details: DigiKeyProductDetails | None = None,
    slot_ids: set[int] | None = None,
) -> NewInventoryItem:
    return NewInventoryItem(
        available_quantity=available_quantity,
        item_description=item_description,
        digikey_part_number=digikey_part_number,
        slot_ids=slot_ids or set(),
        comments="",
        product_details=product_details,
        is_description_placeholder=False,
        digikey_orders=[],
        digikey_barcode_2d=set(),
        digikey_barcode_1d=set(),
        manufacturer_name=None,
        manufacturer_part_number=None,
    )


@pytest.fixture(scope="function")
def inv_repo() -> InventoryRepository:
    return InMemoryRepository(
        {
            ObjectId("123456789012345678901234"): existing_inv_item(
                _id=ObjectId("123456789012345678901234"),
                available_quantity=5,
                item_description="Test item",
                digikey_part_number="TEST123",
            ),
            ObjectId("123456789012345678901235"): existing_inv_item(
                _id=ObjectId("123456789012345678901235"),
                available_quantity=10,
                item_description="Another test item",
                digikey_part_number=None,
            ),
        }
    )


def test_items_frozen(inv_repo: InventoryRepository):
    item = inv_repo[ObjectId("123456789012345678901234")]
    with pytest.raises(ValidationError):
        item.available_quantity = 10


def test_set_existing_item(inv_repo: InventoryRepository):
    item = existing_inv_item(
        _id=ObjectId("123456789012345678901234"),
        available_quantity=15,
        item_description="Updated item",
        digikey_part_number="TEST123",
    )
    inv_repo.set_existing_item(item)
    assert inv_repo[ObjectId("123456789012345678901234")].available_quantity == 15


def test_add_new_item(inv_repo: InventoryRepository):
    new_item = new_inv_item(
        available_quantity=20,
        item_description="New item",
        digikey_part_number="NEW123",
    )
    new_id = inv_repo.add_new(new_item)
    assert inv_repo[new_id].item_description == "New item"


def test_assign_to_slot(inv_repo: InventoryRepository):
    inv_repo.add_to_slot(ObjectId("123456789012345678901234"), 1)
    assert 1 in inv_repo[ObjectId("123456789012345678901234")].slot_ids


def test_get_slot(inv_repo: InventoryRepository):
    inv_repo.add_to_slot(ObjectId("123456789012345678901234"), 1)
    items = inv_repo.get_slot(1)
    assert len(items) == 1
    assert items[0].id == ObjectId("123456789012345678901234")


def test_get_item_by_digikey_part_number(inv_repo: InventoryRepository):
    item = inv_repo.get_item_by_digikey_part_number("TEST123")
    assert item is not None
    assert item.id == ObjectId("123456789012345678901234")


def test_set_comments(inv_repo: InventoryRepository):
    inv_repo.set_comments(ObjectId("123456789012345678901234"), "New comment")
    assert inv_repo[ObjectId("123456789012345678901234")].comments == "New comment"


def test_set_quantity(inv_repo: InventoryRepository):
    inv_repo.set_quantity(ObjectId("123456789012345678901234"), 50)
    assert inv_repo[ObjectId("123456789012345678901234")].available_quantity == 50


def test_set_existing_item_raises_duplicate_error(inv_repo: InventoryRepository):
    item1 = new_inv_item(
        digikey_part_number="12345",
        available_quantity=10,
        item_description="Test item",
    )

    item2 = new_inv_item(
        digikey_part_number="12345",
        slot_ids=set(),
        available_quantity=5,
        item_description="Another test item",
    )
    inv_repo.add_new(item1)
    with pytest.raises(DuplicateDigiKeyPartNumberError):
        inv_repo.add_new(item2)

    # None is ok
    item3 = existing_inv_item(
        _id=ObjectId("123456789012345678901235"),
        available_quantity=10,
        item_description="Another test item",
        digikey_part_number="321",
    )
    inv_repo.set_existing_item(item3)

    # check for 123456789012345678901234
    item4 = existing_inv_item(
        _id=ObjectId("123456789012345678901234"),
        available_quantity=10,
        item_description="Another test item",
        digikey_part_number="12345",
    )
    with pytest.raises(DuplicateDigiKeyPartNumberError):
        inv_repo.set_existing_item(item4)


def test_set_existing_item_raises_key_error(inv_repo: InventoryRepository):
    item = existing_inv_item(
        _id=ObjectId(),
        digikey_part_number="12345",
        available_quantity=10,
        item_description="Test item",
    )
    with pytest.raises(KeyError):
        inv_repo.set_existing_item(item)


def test_assign_to_slot_raises_key_error(inv_repo: InventoryRepository):
    with pytest.raises(KeyError):
        inv_repo.add_to_slot(ObjectId(), 1)


def test_get_slot_raises_key_error(inv_repo: InventoryRepository):
    with pytest.raises(KeyError):
        inv_repo.get_slot(1)


def test_get_item_by_digikey_part_number_raises_key_error(
    inv_repo: InventoryRepository,
):
    assert inv_repo.get_item_by_digikey_part_number("12345") is None


def test_set_comments_raises_key_error(inv_repo: InventoryRepository):
    with pytest.raises(KeyError):
        inv_repo.set_comments(ObjectId(), "New comment")


def test_set_quantity_raises_key_error(inv_repo: InventoryRepository):
    with pytest.raises(KeyError):
        inv_repo.set_quantity(ObjectId(), 100)


def test_set_product_details_raises_key_error(inv_repo: InventoryRepository):
    with pytest.raises(KeyError):
        inv_repo.set_product_details(
            ObjectId(),
            DigiKeyProductDetails(
                datasheet_url="http://example.com/datasheet",
                product_url="http://example.com/product",
                image_url="http://example.com/image",
                detailed_description="Test description",
                product_warnings=[],
            ),
        )


def test_set_product_details(inv_repo: InventoryRepository):
    product_details = DigiKeyProductDetails(
        datasheet_url="http://example.com/datasheet",
        product_url="http://example.com/product",
        image_url="http://example.com/image",
        detailed_description="Test description",
        product_warnings=[],
    )
    inv_repo.set_product_details(ObjectId("123456789012345678901234"), product_details)
    assert (
        inv_repo[ObjectId("123456789012345678901234")].product_details
        == product_details
    )
