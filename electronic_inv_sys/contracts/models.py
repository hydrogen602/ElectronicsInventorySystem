from typing import Annotated, Any, Self
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, PositiveInt
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class ObjectIdPydanticAnnotation:
    @classmethod
    def validate_object_id(cls, v: Any, handler: Any) -> ObjectId:
        if isinstance(v, ObjectId):
            return v

        s: Any = handler(v)
        if ObjectId.is_valid(s):
            return ObjectId(s)
        else:
            raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        assert source_type is ObjectId
        return core_schema.no_info_wrap_validator_function(
            cls.validate_object_id,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: Any, handler: Any
    ) -> JsonSchemaValue:
        return handler(core_schema.str_schema())


class WithId(BaseModel):
    id: Annotated[ObjectId, ObjectIdPydanticAnnotation] = Field(alias="_id")


# TODO: Implement soft delete
# class SoftDelete(BaseModel):
#     is_deleted: bool = Field(default=False, alias="_is_deleted")


class ProductOrderInfo(BaseModel):
    product_description: str | None
    quantity: PositiveInt
    sales_order_id: PositiveInt | None
    invoice_id: PositiveInt | None
    country_of_origin: str | None
    lot_code: str | None
    conflicts: bool = False

    def conflicts_with(self, other: Self) -> bool:
        """
        Returns True if the orders differ in quantity, sales order id, invoice id, country of origin, or lot code.
        """
        # I'm not going to check product_description because it's too subjective
        return (
            (
                self.sales_order_id != other.sales_order_id
                and self.sales_order_id is not None
                and other.sales_order_id is not None
            )
            or (
                self.invoice_id != other.invoice_id
                and self.invoice_id is not None
                and other.invoice_id is not None
            )
            or (
                self.country_of_origin != other.country_of_origin
                and self.country_of_origin is not None
                and other.country_of_origin is not None
            )
            or self.quantity != other.quantity
            or (
                self.lot_code != other.lot_code
                and self.lot_code is not None
                and other.lot_code is not None
            )
        )

    def merge(self, other: Self) -> "ProductOrderInfo":
        # for some reason I can't use Self here???
        if self.conflicts_with(other):
            raise ValueError("Cannot merge conflicting ProductOrderInfo")
        return ProductOrderInfo(
            product_description=self.product_description or other.product_description,
            quantity=self.quantity,
            sales_order_id=self.sales_order_id or other.sales_order_id,
            invoice_id=self.invoice_id or other.invoice_id,
            country_of_origin=self.country_of_origin or other.country_of_origin,
            lot_code=self.lot_code or other.lot_code,
        )


class DigiKeyProductDetails(BaseModel):
    product_url: str | None
    datasheet_url: str | None
    image_url: str | None
    detailed_description: str | None
    product_warnings: list[str] | None


class InventoryItemImport(BaseModel):
    """
    For items being imported from DigiKey into the inventory system.

    They have no id since they are not yet in the inventory system.

    This object MUST NOT be stored in the database.
    """

    quantity: NonNegativeInt
    item_description: str
    is_description_placeholder: bool

    digikey_order: ProductOrderInfo | None
    digikey_barcode_2d: str | None  # not url-encoded, just as it's scanned
    digikey_barcode_1d: str | None
    digikey_part_number: str | None

    manufacturer_part_number: str | None
    manufacturer_name: str | None

    product_details: DigiKeyProductDetails | None


class NewInventoryItem(BaseModel):
    """
    is_description_placeholder is true if no good description is available
    and thus the item_description is some placeholder text or the part number or something.

    Use this class for new items that are not yet in the inventory system.
    Existing items in the inventory system have an ID, and should use ExistingInventoryItemV3.
    """

    available_quantity: NonNegativeInt
    item_description: str
    is_description_placeholder: bool

    slot_ids: set[int]

    digikey_orders: list[ProductOrderInfo]
    digikey_barcode_2d: set[str]  # not url-encoded
    digikey_barcode_1d: set[str]
    comments: str
    digikey_part_number: str | None
    manufacturer_part_number: str | None
    manufacturer_name: str | None

    product_details: DigiKeyProductDetails | None


class ExistingInventoryItem(NewInventoryItem, WithId):
    """
    Items coming from the database have an ID.

    This class is frozen as updates should be done through the repository, not by modifying the object.
    """

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_parent(cls, parent: NewInventoryItem, id: ObjectId) -> Self:
        return cls(**parent.model_dump(), _id=id)


class FusionBomEntry(BaseModel):
    package: str
    category: str | None
    manufacturer_part_number: str | None
    mpn: str | None


class BomEntry(BaseModel):
    qty: int
    value: str | None
    device: str
    parts: list[str]
    description: str | None
    manufacturer: str | None
    comments: str
    inventory_item_mapping_ids: set[Annotated[ObjectId, ObjectIdPydanticAnnotation]]
    fusion360_ext: FusionBomEntry | None


class ProjectInfo(BaseModel):
    name: str | None
    author_names: str | None
    comments: str

    @classmethod
    def empty(cls) -> "ProjectInfo":
        return cls(name=None, author_names=None, comments="")


class NewBom(BaseModel):
    """BOM without an ID, for creating new BOMs."""

    info_line: str
    """Info parsed from the BOM file."""
    project: ProjectInfo
    rows: list[BomEntry]
    """The list of BOM entries."""
    name: str | None = None
    """Optional name for the BOM."""


class ExistingBom(NewBom, WithId):
    """
    BOMs coming from the database have an ID.

    This class is frozen as updates should be done through the repository, not by modifying the object.
    """

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_parent(cls, parent: NewBom, id: ObjectId) -> Self:
        return cls(**parent.model_dump(), _id=id)
