from typing import Annotated
from bson import ObjectId
from pydantic import AfterValidator, BaseModel, Field

from electronic_inv_sys.contracts.models import ObjectIdPydanticAnnotation


def from_hex(value: str) -> int:
    return int(value, 16)


def not_numeric_barcode(value: str) -> str:
    if value.strip().isnumeric():
        raise ValueError("Barcode cannot be numeric")
    return value


def digikey_legacy_barcode(value: str) -> str:
    value = value.strip()
    if not value.isnumeric():
        raise ValueError("Barcode must be all digits")
    if len(value) != 22:
        raise ValueError("Barcode must be 22 digits")

    return value


def pack_list_1D_barcode(value: str) -> str:
    if not value.isnumeric():
        raise ValueError("Barcode must be all digits")
    if len(value) != 26:
        raise ValueError("Barcode must be 26 digits")
    return value


# def all_numeric(value: str) -> str:
#     if not value.isnumeric():
#         raise ValueError("ID must be all digits")
#     return value


type HexSlotId = Annotated[str, AfterValidator(from_hex)]
type Barcode2D = Annotated[str, AfterValidator(not_numeric_barcode)]
type Barcode1D = Annotated[str, AfterValidator(digikey_legacy_barcode)]

type PackList1DBarcode = Annotated[str, AfterValidator(pack_list_1D_barcode)]


class AddItemByBarcodeRequest(BaseModel):
    barcode: Barcode2D | Barcode1D


class AddManyItemsByBarcodeRequest(BaseModel):
    barcode: Barcode2D | PackList1DBarcode


class SetComments(BaseModel):
    id: Annotated[ObjectId, ObjectIdPydanticAnnotation] = Field(alias="_id")
    comments: str | None = None


class AddItemByBarcodeRequestIPhone(BaseModel):
    slot_ids: list[HexSlotId] | HexSlotId
    barcode: Barcode2D | Barcode1D
