from electronic_inv_sys.contracts.models import InventoryItemImport, NewInventoryItem


def map_inv_item_import_to_inv_item(item: InventoryItemImport) -> NewInventoryItem:
    return NewInventoryItem(
        available_quantity=item.quantity,
        item_description=item.item_description,
        is_description_placeholder=item.is_description_placeholder,
        digikey_orders=[item.digikey_order] if item.digikey_order else [],
        digikey_barcode_2d=(
            {item.digikey_barcode_2d} if item.digikey_barcode_2d else set()
        ),
        digikey_barcode_1d=(
            {item.digikey_barcode_1d} if item.digikey_barcode_1d else set()
        ),
        digikey_part_number=item.digikey_part_number,
        manufacturer_name=item.manufacturer_name,
        manufacturer_part_number=item.manufacturer_part_number,
        product_details=item.product_details,
        slot_ids=set(),
        comments="",
    )
