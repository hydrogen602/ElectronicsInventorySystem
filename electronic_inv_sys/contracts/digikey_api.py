from abc import ABC, abstractmethod

from electronic_inv_sys.contracts.digikey_models.barcoding import (
    PackListBarcodeResponse,
    Product2DBarcodeResponse,
    ProductBarcodeResponse,
)
from electronic_inv_sys.contracts.digikey_models.packlist import (
    InvoicePackingList,
    SalesOrderPackList,
)
from electronic_inv_sys.contracts.digikey_models.product_search import ProductDetails


class DigiKeyAPIException(Exception):
    """
    Thrown if the API is unavailable, returns an error, or returns gibberish.
    """

    pass


class DigiKeyAPI(ABC):
    @abstractmethod
    async def get_item_by_1d_barcode(
        self, barcode1d: str
    ) -> ProductBarcodeResponse: ...

    @abstractmethod
    async def get_item_by_2d_barcode(
        self, barcode2d: str
    ) -> Product2DBarcodeResponse: ...

    @abstractmethod
    async def get_pack_list_by_1d_barcode(
        self, barcode1d: str
    ) -> PackListBarcodeResponse: ...

    @abstractmethod
    async def get_pack_list_by_2d_barcode(
        self, barcode2d: str
    ) -> PackListBarcodeResponse: ...

    @abstractmethod
    async def get_pack_list_by_invoice_id(
        self, invoice_id: int
    ) -> InvoicePackingList: ...

    @abstractmethod
    async def get_pack_list_by_sales_order_id(
        self, sales_order_id: int
    ) -> SalesOrderPackList: ...

    @abstractmethod
    async def get_product_details(self, digikey_part_id: str) -> ProductDetails: ...
