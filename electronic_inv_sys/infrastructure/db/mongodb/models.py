from typing import Self
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, NonNegativeInt, PositiveInt

from electronic_inv_sys.contracts.models import (
    WithId,
)


class MongoProductOrderInfo(BaseModel):
    product_description: str | None
    quantity: PositiveInt
    sales_order_id: PositiveInt | None
    invoice_id: PositiveInt | None
    country_of_origin: str | None
    lot_code: str | None


class MongoDigiKeyProductDetails(BaseModel):
    product_url: str | None
    datasheet_url: str | None
    image_url: str | None
    detailed_description: str | None
    product_warnings: list[str] | None


class MongoNewInventoryItem(BaseModel):
    """
    is_description_placeholder is true if no good description is available
    and thus the item_description is some placeholder text or the part number or something.

    Use this class for new items that are not yet in the inventory system.
    Existing items in the inventory system have an ID, and should use ExistingInventoryItemV3.
    """

    available_quantity: NonNegativeInt
    item_description: str
    is_description_placeholder: bool

    slot_ids: dict[str, None]  # int stored as str because of bson only does string keys

    digikey_orders: list[MongoProductOrderInfo]
    digikey_barcode_2d: dict[str, None]  # not url-encoded, mongodb doesn't do sets
    digikey_barcode_1d: dict[str, None]
    comments: str
    digikey_part_number: str | None
    manufacturer_part_number: str | None
    manufacturer_name: str | None

    product_details: MongoDigiKeyProductDetails | None


class MongoExistingInventoryItem(MongoNewInventoryItem, WithId):
    """
    Items coming from the database have an ID.

    This class is frozen as updates should be done through the repository, not by modifying the object.
    """

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_parent(cls, parent: MongoNewInventoryItem, id: ObjectId) -> Self:
        return cls(**parent.model_dump(), _id=id)


class MongoFusionBomEntry(BaseModel):
    package: str
    category: str | None
    manufacturer_part_number: str | None
    mpn: str | None


class MongoBomEntry(BaseModel):
    qty: int
    value: str | None
    device: str
    parts: list[str]
    description: str | None
    manufacturer: str | None
    comments: str
    inventory_item_mapping_ids: set[ObjectId]
    fusion360_ext: MongoFusionBomEntry | None


class MongoProjectInfo(BaseModel):
    name: str | None
    author_names: str | None
    comments: str


class MongoNewBom(BaseModel):
    info_line: str
    project: MongoProjectInfo
    rows: list[MongoBomEntry]
    name: str | None = None


class MongoExistingBom(MongoNewBom, WithId):
    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_parent(cls, parent: MongoNewBom, id: ObjectId) -> Self:
        return cls(**parent.model_dump(), _id=id)
