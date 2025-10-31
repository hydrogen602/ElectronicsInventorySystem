from electronic_inv_sys.contracts.digikey_models.barcoding import (
    PackListBarcodeResponse,
    Product2DBarcodeResponse,
    ProductBarcodeResponse,
)
from electronic_inv_sys.contracts.models import (
    InventoryItemImport,
    ProductOrderInfo,
)


def map_product_barcode_import_item(
    product: ProductBarcodeResponse | Product2DBarcodeResponse, barcode: str
) -> InventoryItemImport:

    if isinstance(product, ProductBarcodeResponse):
        return InventoryItemImport(
            quantity=product.Quantity,
            item_description=product.ProductDescription,
            is_description_placeholder=False,
            digikey_order=ProductOrderInfo(
                product_description=product.ProductDescription,
                quantity=product.Quantity,
                sales_order_id=None,
                invoice_id=None,
                country_of_origin=None,
                lot_code=None,
            ),
            digikey_barcode_2d=None,
            digikey_barcode_1d=barcode,
            digikey_part_number=product.DigiKeyPartNumber,
            manufacturer_part_number=product.ManufacturerPartNumber,
            manufacturer_name=product.ManufacturerName,
            product_details=None,
        )
    else:
        return InventoryItemImport(
            quantity=product.Quantity,
            item_description=product.ProductDescription or product.DigiKeyPartNumber,
            is_description_placeholder=product.ProductDescription is None,
            digikey_order=ProductOrderInfo(
                product_description=product.ProductDescription,
                quantity=product.Quantity,
                sales_order_id=product.SalesorderId,
                invoice_id=product.InvoiceId,
                country_of_origin=product.CountryOfOrigin,
                lot_code=product.LotCode,
            ),
            digikey_barcode_2d=barcode,
            digikey_barcode_1d=None,
            digikey_part_number=product.DigiKeyPartNumber,
            manufacturer_part_number=product.ManufacturerPartNumber,
            manufacturer_name=product.ManufacturerName,
            product_details=None,
        )


def map_pack_list_to_import_items(
    pack_list: PackListBarcodeResponse,
) -> list[InventoryItemImport]:
    return [
        InventoryItemImport(
            quantity=item.Quantity,
            item_description=item.DigiKeyPartNumber,
            is_description_placeholder=True,
            digikey_order=ProductOrderInfo(
                product_description=None,
                quantity=item.Quantity,
                sales_order_id=pack_list.SalesorderId,
                invoice_id=pack_list.InvoiceId,
                country_of_origin=None,
                lot_code=None,
            ),
            digikey_barcode_2d=None,
            digikey_barcode_1d=None,
            digikey_part_number=item.DigiKeyPartNumber,
            manufacturer_part_number=None,
            manufacturer_name=None,
            product_details=None,
        )
        for item in pack_list.PackListDetails
    ]
