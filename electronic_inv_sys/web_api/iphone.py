"""
APIs that make it easier to call from the iPhone's shortcuts app or interact via Siri.
"""

from typing import Annotated
from fastapi import APIRouter, Depends

from electronic_inv_sys.contracts.models import ExistingInventoryItem
from electronic_inv_sys.services import Services, ServicesProviderSingleton
from electronic_inv_sys.web_api.api_models import (
    AddItemByBarcodeRequestIPhone,
    HexSlotId,
)
from electronic_inv_sys.web_api.common_commands import import_by_barcode
from electronic_inv_sys.web_api.english_utils import (
    replace_written_digits_with_numbers,
    sp,
)


router = APIRouter()


@router.get("/slot/{slot_id_hex}")
async def get_inventory(
    slot_id_hex: str,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> str:
    """
    Produce a message suitable to be announced by Siri.
    """
    slot_id_hex = slot_id_hex.lower()
    slot_id_hex = replace_written_digits_with_numbers(slot_id_hex)
    # strip out all whitespace
    slot_id_hex = "".join(slot_id_hex.split())

    # Siri is dumb sometimes
    slot_id_hex = slot_id_hex.replace("siri", "3")

    try:
        slot_id = int(slot_id_hex, 16)
    except ValueError:
        return f"Invalid slot ID: expected a hex number, but got {slot_id_hex}"

    slot_id_hex_siri_friendly = "-".join(
        f"{slot_id:x}"
    )  # put in dashes so that siri says F, A instead of Fa, etc.

    try:
        items = services.inventory.get_slot(int(slot_id))
    except KeyError:
        return f"No items found for slot {slot_id_hex_siri_friendly}"

    def one_item_text(item: ExistingInventoryItem) -> str:
        comments_addon = ""
        if item.comments.strip():
            comments_addon = f"Additional comments: {item.comments.strip()}"

        quantity_str = f"{item.available_quantity} {sp(item.available_quantity, 'item is', 'items are')} available"

        manufacturer_part = (
            f"made by {item.manufacturer_name}" if item.manufacturer_name else ""
        )

        description = (
            item.item_description if item.item_description else "No description found"
        )

        return f"{description}. {manufacturer_part}. {quantity_str}. {comments_addon}"

    match items:
        case []:
            raise RuntimeError(
                "Should not have gotten here - a KeyError should have been raised"
            )
        case [item]:
            return one_item_text(item)
        case many:
            preamble = f"Found {len(items)} items in slot {slot_id_hex_siri_friendly}:"
            texts = [
                f"...Item {i+1}: {one_item_text(item)}" for i, item in enumerate(many)
            ]
            return f"{preamble}. {'\n'.join(texts)}"


@router.post("/item")
async def add_item_by_barcode_and_assign_slots(
    request: AddItemByBarcodeRequestIPhone,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingInventoryItem:
    barcode = request.barcode.strip()

    def convert_one(slot_id_hex: HexSlotId) -> int:
        if isinstance(slot_id_hex, int):
            return slot_id_hex
        try:
            return int(slot_id_hex, 16)
        except ValueError:
            raise ValueError(
                f"Invalid slot ID: expected a hex number, but got {slot_id_hex}"
            )

    slot_ids_ls = (
        request.slot_ids if isinstance(request.slot_ids, list) else [request.slot_ids]
    )

    slot_ids = [convert_one(slot_id_hex) for slot_id_hex in slot_ids_ls]

    item = await import_by_barcode(barcode, services)

    for slot_id in slot_ids:
        services.inventory.add_to_slot(item.id, slot_id)

    return services.inventory[item.id]
