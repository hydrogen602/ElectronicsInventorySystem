from fastapi import HTTPException
from loguru import logger
from electronic_inv_sys.contracts.models import ExistingInventoryItem
from electronic_inv_sys.infrastructure.digikey_mappers import (
    map_product_barcode_import_item,
)
from electronic_inv_sys.logic.importer import new_item_importer
from electronic_inv_sys.logic.importer.merge import (
    ManufacturerInfoMismatchError,
)
from electronic_inv_sys.services import Services


async def import_by_barcode(barcode: str, services: Services) -> ExistingInventoryItem:
    if barcode.isdigit():
        # if its only digits, then this was the 1D legacy barcode
        product_info = await services.digikey_api.get_item_by_1d_barcode(barcode)
    else:
        product_info = await services.digikey_api.get_item_by_2d_barcode(barcode)

    item = map_product_barcode_import_item(product_info, barcode)
    logger.info("Importing item: {}", item)

    try:
        obj_id, _ = await new_item_importer(
            item, services.inventory, services.digikey_api, services.config
        )

    except ManufacturerInfoMismatchError as e:
        logger.opt(exception=e).error(
            "Mismatch in manufacturer info: Failed to update product details for item {item}: {e}",
            item=item,
            e=e,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Manufacturer info mismatch: {e}",
        )
    except Exception as e:
        logger.opt(exception=e).error(
            "Failed to update product details for item {item}: {e}", item=item, e=e
        )
        raise HTTPException(status_code=500, detail="Failed to update product details")

    try:
        return services.inventory[obj_id]
    except KeyError:
        raise HTTPException(
            status_code=500,
            detail="Item that was just imported not found. This is an internal error.",
        )
