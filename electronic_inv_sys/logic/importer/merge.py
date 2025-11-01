from enum import Enum
from bson import ObjectId
from loguru import logger
from electronic_inv_sys.logic.importer.mapping import map_inv_item_import_to_inv_item
from electronic_inv_sys.contracts.models import (
    DigiKeyProductDetails,
    ExistingInventoryItem,
    InventoryItemImport,
    ProductOrderInfo,
)
from electronic_inv_sys.contracts.repos import ConfigRepository, InventoryRepository
from electronic_inv_sys.util import ots, relatively_similar


class ManufacturerInfoMismatchError(Exception):
    """
    When two parts have the same digikey part number but different manufacturer part numbers or manufacturer names.
    """

    def __init__(self, num1: str, num2: str, *args: object) -> None:
        self.num1 = num1
        self.num2 = num2
        super().__init__(f"Manufacturer info mismatch: '{num1}' vs '{num2}'", *args)

    pass


class OrderInfoMismatchError(Exception):
    """
    When two order details have the same invoice id but different order details
    """

    def __init__(
        self, one: ProductOrderInfo, two: ProductOrderInfo, *args: object
    ) -> None:
        self.one = one
        self.two = two
        super().__init__(
            "Order info mismatch",
            one,
            two,
            *args,
        )

    pass


class MergeResult(Enum):
    """
    NewItemWithoutDigikeyNumber
    NewItemWithDigikeyNumber
    NewItemMergedIntoExistingStock
      - increases the quantity

    DuplicateOrder - does not increase the quantity
    """

    NewItemWithoutDigikeyNumber = 1
    NewItemWithDigikeyNumber = 2
    NewItemMergedIntoExistingStock = 3
    DuplicateOrder = 4


def merge_and_import_item(
    import_item: InventoryItemImport,
    repo: InventoryRepository,
    config: ConfigRepository,
) -> tuple[ObjectId, MergeResult]:
    """
    Import a new item into the inventory.

    This is the action to call when a new item is received in the warehouse/inventory system.
    Thus if an entry with the same digikey part number already exists, it will merge this into the existing entry.
    Merge rules:
    - available_quantity is increased by the new item's quantity
    - item_description is overwritten if the existing description is a placeholder
    - is_description_placeholder
      - if the existing description is not a placeholder, nothing changes and is_description_placeholder=False
      - if the existing description is a placeholder, is_description_placeholder is set to the new item's value
    - digikey_order is appended to the list (if not already in the list, otherwise ignored)
    - digikey_barcode_2d is added to the set
    - digikey_barcode_1d is added to the set
    - digikey_part_number - no op - we only end up in this situation if the part number is the same
    - manufacturer_part_number
      - if not set, set to the new item's manufacturer part number
      - if set and different, throw ManufacturerInfoMismatchError
    - manufacturer_name
      - if not set, set to the new item's manufacturer name
      - if set and different, throw ManufacturerInfoMismatchError
    - product_details is overwritten if the new item has product details

    Config:
        strict_order_matching: If true, requires that the digikey part number, order, and invoice id are set on the import item.
            This makes matching up orders more reliable to ensure the same order is not counted twice in the quantity.

    Args:
        item (InventoryItemV3): The item to import.
    Returns:
        ObjectId: The ID of the imported item.
    Throws:
        ManufacturerInfoMismatchError: If the manufacturer part number or manufacturer name of the new item
            does not match the existing item.
    """

    if config.get_as_bool(type(config).STRICT_ORDER_MATCHING_KEY, default=False):
        if import_item.digikey_part_number is None:
            raise ValueError(
                "Cannot use strict order matching without a digikey part number"
            )
        if import_item.digikey_order is None:
            raise ValueError("Cannot use strict order matching without an order")
        if import_item.digikey_order.invoice_id is None:
            raise ValueError("Cannot use strict order matching without an invoice id")

    new_digikey_part_number = import_item.digikey_part_number

    if new_digikey_part_number is None:
        # nothing to match -> just import
        logger.info("Importing new item without digikey number: {}", import_item)
        new_inv_item = map_inv_item_import_to_inv_item(import_item)
        return repo.add_new(new_inv_item), MergeResult.NewItemWithoutDigikeyNumber

    existing_item = repo.get_item_by_digikey_part_number(new_digikey_part_number)

    if existing_item is None:
        # no existing item -> just import
        logger.info("Importing new item: {}", import_item)
        new_inv_item = map_inv_item_import_to_inv_item(import_item)
        return repo.add_new(new_inv_item), MergeResult.NewItemWithDigikeyNumber

    assert existing_item.digikey_part_number == new_digikey_part_number

    # check for manufacturer info mismatch
    manufacturer_part_number: str | None
    match (
        existing_item.manufacturer_part_number,
        import_item.manufacturer_part_number,
    ):
        case (None, None):
            manufacturer_part_number = None
        case (None, some):
            manufacturer_part_number = some
        case (some, None):
            manufacturer_part_number = some
        case (some1, some2) if some1 == some2 or relatively_similar(some1, some2):
            manufacturer_part_number = some1
        case (some1, some2):
            raise ManufacturerInfoMismatchError(some1, some2)

    manufacturer_name: str | None
    match (existing_item.manufacturer_name, import_item.manufacturer_name):
        case (None, None):
            manufacturer_name = None
        case (None, some):
            manufacturer_name = some
        case (some, None):
            manufacturer_name = some
        case (some1, some2) if some1 == some2 or relatively_similar(some1, some2):
            manufacturer_name = some1
        case (some1, some2):
            raise ManufacturerInfoMismatchError(some1, some2)

    merged_orders, order_merge_result = _merge_order_details(
        existing_item.digikey_orders, import_item.digikey_order
    )

    merge_result = MergeResult.NewItemMergedIntoExistingStock

    match order_merge_result:
        case MergeOrderResult.NoOrder:
            merged_quantity = existing_item.available_quantity + import_item.quantity
        case MergeOrderResult.New:
            merged_quantity = existing_item.available_quantity + import_item.quantity
        case MergeOrderResult.Duplicate:
            merged_quantity = existing_item.available_quantity
            merge_result = MergeResult.DuplicateOrder

    # existing item -> merge
    merged_item = ExistingInventoryItem(
        _id=existing_item.id,
        # available_quantity is increased by the new item's quantity
        available_quantity=merged_quantity,
        # item_description is overwritten if the existing description is a placeholder
        item_description=(
            import_item.item_description
            if existing_item.is_description_placeholder
            else existing_item.item_description
        ),
        is_description_placeholder=existing_item.is_description_placeholder
        and import_item.is_description_placeholder,
        slot_ids=existing_item.slot_ids,
        digikey_orders=merged_orders,
        digikey_barcode_2d=(
            existing_item.digikey_barcode_2d | ots(import_item.digikey_barcode_2d)
        ),
        digikey_barcode_1d=(
            existing_item.digikey_barcode_1d | ots(import_item.digikey_barcode_1d)
        ),
        comments=existing_item.comments,
        digikey_part_number=existing_item.digikey_part_number,
        manufacturer_part_number=manufacturer_part_number,
        manufacturer_name=manufacturer_name,
        product_details=_merge_product_details(
            existing_item.product_details, import_item.product_details
        ),
    )

    match merge_result:
        case MergeResult.NewItemMergedIntoExistingStock:
            logger.info("Merging new item into existing stock: {}", merged_item)
        case MergeResult.DuplicateOrder:
            logger.info("Duplicate order: {}", merged_item)

    repo.set_existing_item(merged_item)
    return merged_item.id, merge_result


class MergeOrderResult(Enum):
    NoOrder = 0
    New = 1
    Duplicate = 2


def _merge_order_details(
    existing: list[ProductOrderInfo], new: ProductOrderInfo | None
) -> tuple[list[ProductOrderInfo], MergeOrderResult]:
    if new is None:
        return existing, MergeOrderResult.NoOrder

    # Allow multiple orders with the same invoice id and sales order id.
    # Only merge when the new entry is effectively identical to an existing one.

    ls: list[ProductOrderInfo] = []
    merge_result = MergeOrderResult.New

    found = False
    conflicts = False
    for order in existing:
        if order.invoice_id == new.invoice_id:
            if order.conflicts_with(new):
                # Sometimes digikey sends the same part in the same order in multiple bags.
                # Here we have 2 orders that differ somewhere
                conflicts = True
                ls.append(order)  # keep both orders
                logger.info("Conflicts with existing order: {}", order)
                continue  # raise OrderInfoMismatchError(order, new)
            merged_new = order.merge(new)
            merge_result = MergeOrderResult.Duplicate
            ls.append(merged_new)
            found = True
        else:
            ls.append(order)

    if not found:
        new.conflicts = conflicts
        ls.append(new)

    return ls, merge_result


def _merge_product_details(
    existing: DigiKeyProductDetails | None, new: DigiKeyProductDetails | None
) -> DigiKeyProductDetails | None:
    if existing is None:
        return new
    if new is None:
        return existing

    return DigiKeyProductDetails(
        product_url=new.product_url if new.product_url else existing.product_url,
        datasheet_url=(
            new.datasheet_url if new.datasheet_url else existing.datasheet_url
        ),
        image_url=new.image_url if new.image_url else existing.image_url,
        detailed_description=(
            new.detailed_description
            if new.detailed_description
            else existing.detailed_description
        ),
        product_warnings=(
            new.product_warnings if new.product_warnings else existing.product_warnings
        ),
    )
