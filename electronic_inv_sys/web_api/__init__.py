# pyright: reportUnusedFunction=false

from typing import Annotated, Any, cast
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from loguru import logger
import io
import csv

from electronic_inv_sys.contracts.models import (
    BomEntry,
    ExistingBom,
    FusionBomEntry,
    NewBom,
)
from electronic_inv_sys.logic.bom import BomSource
from electronic_inv_sys.util import Environment
from electronic_inv_sys.web_api.api_models import (
    AddItemByBarcodeRequest,
    AddManyItemsByBarcodeRequest,
)
from electronic_inv_sys.contracts.digikey_models.barcoding import (
    PackListBarcodeResponse,
)
from electronic_inv_sys.contracts.models import (
    ExistingInventoryItem,
    ObjectIdPydanticAnnotation,
)
from electronic_inv_sys.infrastructure.digikey_mappers import (
    map_pack_list_to_import_items,
)
from electronic_inv_sys.logic.importer import new_item_importer, update_product_details
from electronic_inv_sys.logic.importer.merge import (
    ManufacturerInfoMismatchError,
    OrderInfoMismatchError,
)
from electronic_inv_sys.services import Services, ServicesProviderSingleton
from electronic_inv_sys.web_api.common_commands import import_by_barcode
from electronic_inv_sys.web_api.iphone import router as iphone_router

# Note: after editing the API, run `make prepare-build` to regenerate the OpenAPI spec

router = APIRouter()

# routes to make it easier to use with iPhone's shortcuts app and Siri
router.include_router(iphone_router, prefix="/iphone")


@router.get("/env")
def get_env(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> Environment:
    return services.config.environment


@router.get("/slot/{slot_id}")
def get_inventory(
    slot_id: int,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingInventoryItem]:
    return services.inventory.get_slot(slot_id)


@router.post("/item")
async def add_item_by_barcode(
    request: AddItemByBarcodeRequest,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingInventoryItem:
    barcode = request.barcode.strip()

    return await import_by_barcode(barcode, services)


@router.post("/items")
async def add_items_by_pack_list_barcode(
    pack_list_barcode: AddManyItemsByBarcodeRequest,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingInventoryItem]:
    barcode = pack_list_barcode.barcode.strip()

    pack_list: PackListBarcodeResponse
    if barcode.isdigit():
        pack_list = await services.digikey_api.get_pack_list_by_1d_barcode(barcode)
    else:
        pack_list = await services.digikey_api.get_pack_list_by_2d_barcode(barcode)

    items = map_pack_list_to_import_items(pack_list)
    logger.info("Importing items: {}", items)

    obj_ids: list[ObjectId] = []
    for item in items:
        try:
            obj_id, _ = await new_item_importer(
                item, services.inventory, services.digikey_api, services.config
            )
            obj_ids.append(obj_id)
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
        except OrderInfoMismatchError as e:
            logger.opt(exception=e).error(
                "Mismatch in order info: Failed to update product details for item {item}: {e}",
                item=item,
                e=e,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Order info mismatch: {e}",
            )
        except Exception as e:
            logger.opt(exception=e).error(
                "Failed to update product details for item {item}: {e}",
                item=item,
                e=e,
            )
            raise HTTPException(
                status_code=500, detail="Failed to update product details"
            )

    try:
        return [services.inventory[obj_id] for obj_id in obj_ids]
    except KeyError:
        raise HTTPException(
            status_code=500,
            detail="Item that was just imported not found. This is an internal error.",
        )


@router.get("/items")
def get_all_items(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingInventoryItem]:
    return list(services.inventory.values())


@router.get("/item/{item_id}")
def get_item(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingInventoryItem:
    return services.inventory[item_id]


@router.post("/item/{item_id}/update_details")
async def update_item_details(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    try:
        await update_product_details(
            services.inventory[item_id], services.inventory, services.digikey_api
        )
    except Exception as e:
        logger.error(f"Failed to update product details for item {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update product details")


@router.post("/items/update_details")
async def update_all_items_details(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    items = services.inventory.values()
    logger.info(f"Updating product details for {len(items)} items")
    for item in items:
        try:
            await update_product_details(item, services.inventory, services.digikey_api)
        except Exception as e:
            logger.error(f"Failed to update product details for item {item.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update product details for item {item.id}",
            )


@router.post("/item/{item_id}/comments")
def set_comments(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    comments: str,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    services.inventory.set_comments(item_id, comments)


@router.post("/item/{item_id}/quantity")
def set_quantity(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    quantity: int,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    services.inventory.set_quantity(item_id, quantity)


@router.put("/item/{item_id}/slot/{slot_id}")
def add_item_to_slot(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    slot_id: int,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    services.inventory.add_to_slot(item_id, slot_id)


@router.delete("/item/{item_id}/slot/{slot_id}")
def remove_item_from_slot(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    slot_id: int,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    services.inventory.remove_from_slot(item_id, slot_id)


@router.get("/item/{item_id}/slots")
def get_slots_of_item(
    item_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> set[int]:
    return services.inventory.get_slots_of_item(item_id)


@router.get("/search")
def search(
    query: str,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingInventoryItem]:
    return services.inventory.text_search(query)


@router.get("/search/match-bom-entry")
def match_bom_entry(
    search: str,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingInventoryItem]:
    """
    the openapi-generator for typescript-fetch has a bug when dealing with lists of lists,
    so I'm only doing one item at a time for now
    """
    return services.inventory.text_search(search, max_results=5)


def parse_bom_source(src: str) -> BomSource:
    try:
        return BomSource(src)
    except ValueError:
        valid_sources = [source.value for source in BomSource]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source '{src}'. Valid sources: {', '.join(valid_sources)}",
        )


@router.post("/bom/parse/gerber-export")
async def upload_zip(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
    file: UploadFile = File(...),
    src: str = Query(..., description="BOM source (e.g., 'fusion360')"),
) -> NewBom:
    if file.content_type not in ("application/zip", "application/x-zip-compressed"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only ZIP files are accepted."
        )

    bom_source = parse_bom_source(src)

    zip_content = await file.read()
    return services.bom_analysis.gerber_bom_analysis(zip_content, bom_source)


@router.post("/bom/parse/gerber-export/csv")
async def upload_zip_to_csv(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
    file: UploadFile = File(...),
    src: str = Query(..., description="BOM source (e.g., 'fusion360')"),
) -> StreamingResponse:
    if file.content_type not in ("application/zip", "application/x-zip-compressed"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only ZIP files are accepted."
        )

    bom_source = parse_bom_source(src)

    zip_content = await file.read()
    rows: list[BomEntry] = services.bom_analysis.gerber_bom_analysis(
        zip_content, bom_source
    ).rows

    if not rows:
        raise HTTPException(
            status_code=404, detail="No BOM entries found in the uploaded file."
        )

    output = io.StringIO()
    writer = csv.writer(output)

    headers = list(FusionBomEntry.model_fields.keys())
    writer.writerow(headers)

    for row in rows:
        row_values: list[Any] = []
        for field in headers:
            value: Any = getattr(row, field)
            if isinstance(value, list):
                row_values.append(",".join(map(str, cast(list[Any], value))))
            else:
                row_values.append(value)
        writer.writerow(row_values)

    stream = io.BytesIO(output.getvalue().encode("utf-8"))
    return StreamingResponse(
        content=stream,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bom.csv"},
    )


@router.get("/bom")
def get_all_boms(
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> list[ExistingBom]:
    """Get all BOMs."""
    return list(services.bom.values())


@router.get("/bom/{bom_id}")
def get_bom(
    bom_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingBom:
    """Get a single BOM by ID."""
    return services.bom[bom_id]


@router.post("/bom")
def create_bom(
    bom: NewBom,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingBom:
    """Create a new BOM."""
    bom_id = services.bom.add_new(bom)
    return services.bom[bom_id]


@router.put("/bom/{bom_id}")
def update_bom(
    bom_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    bom: ExistingBom,
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> ExistingBom:
    """Update an existing BOM."""
    if bom_id != bom.id:
        raise HTTPException(
            status_code=400, detail="BOM ID in path does not match BOM ID in body"
        )
    services.bom.set_existing_item(bom)
    return services.bom[bom_id]


@router.delete("/bom/{bom_id}")
def delete_bom(
    bom_id: Annotated[ObjectId, ObjectIdPydanticAnnotation],
    services: Annotated[Services, Depends(ServicesProviderSingleton.services)],
) -> None:
    """Delete a BOM by ID."""
    try:
        del services.bom[bom_id]
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="BOM deletion is not supported")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"BOM with ID {bom_id} not found")
