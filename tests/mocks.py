from electronic_inv_sys.contracts.digikey_models.barcoding import ProductBarcodeResponse
from electronic_inv_sys.infrastructure.digikey_api import DigiKeyAPIImpl


class DigiKeyAPIImplModified(DigiKeyAPIImpl):
    async def get_item_by_1d_barcode(self, barcode1d: str) -> ProductBarcodeResponse:
        return ProductBarcodeResponse(
            DigiKeyPartNumber="TEST123",
            ManufacturerPartNumber="TEST123",
            ManufacturerName="TEST123",
            ProductDescription="TEST123",
            Quantity=1,
        )
