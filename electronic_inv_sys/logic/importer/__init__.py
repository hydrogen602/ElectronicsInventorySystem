from bson import ObjectId
from loguru import logger
from electronic_inv_sys.logic.details_update import (
    refine_product_details,
)
from electronic_inv_sys.logic.importer.merge import MergeResult, merge_and_import_item
from electronic_inv_sys.contracts.digikey_api import DigiKeyAPI, DigiKeyAPIException
from electronic_inv_sys.contracts.models import (
    ExistingInventoryItem,
    InventoryItemImport,
)
from electronic_inv_sys.contracts.repos import ConfigRepository, InventoryRepository


async def new_item_importer(
    item: InventoryItemImport,
    repo: InventoryRepository,
    digikey_api: DigiKeyAPI,
    config: ConfigRepository,
) -> tuple[ObjectId, MergeResult]:
    """
    Tries to fetch missing details from DigiKey API and imports the item into the inventory.

    Top-level for import logic

    Throws:
        ManufacturerInfoMismatchError: If the manufacturer part number or manufacturer name of the new item
            does not match the existing item (if it exists). (Digikey part number is used as the unique identifier)
    """

    if item.digikey_part_number is not None and (
        item.product_details is None
        or item.manufacturer_name is None
        or item.manufacturer_part_number is None
        or item.is_description_placeholder is True
    ):
        try:
            raw_details = (
                await digikey_api.get_product_details(item.digikey_part_number)
            ).Product
        except DigiKeyAPIException as e:
            logger.warning(
                f"Failed to fetch product details for {item.digikey_part_number}: {e}"
            )
            raw_details = None  # its best-effort, so we can continue even if we fail

        if raw_details is not None:

            if item.product_details is None:
                item.product_details = refine_product_details(raw_details)

            if item.manufacturer_name is None and raw_details.Manufacturer is not None:
                item.manufacturer_name = raw_details.Manufacturer.Name

            if item.manufacturer_part_number is None:
                item.manufacturer_part_number = raw_details.ManufacturerProductNumber

            if (
                item.is_description_placeholder
                and raw_details.Description is not None
                and raw_details.Description.ProductDescription
            ):
                item.item_description = raw_details.Description.ProductDescription
                item.is_description_placeholder = False

    return merge_and_import_item(item, repo, config)


async def update_product_details(
    item: ExistingInventoryItem, repo: InventoryRepository, digikey_api: DigiKeyAPI
) -> None:
    """
    Updates the product details of an inventory item.

    Args:
        item (ExistingInventoryItem): The item to update.

    Raises:
        ValueError: If the item does not have a DigiKey part number.
        DigiKeyAPIException: If the API call fails or no product details are returned (but the product was still found).
    """
    if item.digikey_part_number is None:
        raise ValueError(f"Item {item.id} does not have a DigiKey part number")

    raw_details = (
        await digikey_api.get_product_details(item.digikey_part_number)
    ).Product

    if raw_details is None:
        raise DigiKeyAPIException(
            f"Failed to fetch product details for {item.digikey_part_number}"
        )

    repo.set_product_details(item.id, refine_product_details(raw_details))
