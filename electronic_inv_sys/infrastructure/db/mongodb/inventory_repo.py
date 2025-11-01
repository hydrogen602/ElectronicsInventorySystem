from typing import Any
from bson.objectid import ObjectId
from automapper import Mapper  # pyright: ignore[reportMissingTypeStubs]

from electronic_inv_sys.contracts.models import (
    DigiKeyProductDetails,
    ExistingInventoryItem,
    NewInventoryItem,
    ProductOrderInfo,
)
from electronic_inv_sys.contracts.repos import (
    DuplicateDigiKeyPartNumberError,
    InventoryRepository,
)
from electronic_inv_sys.infrastructure.db.mongodb import MongoDataDB
from electronic_inv_sys.infrastructure.db.mongodb.bom_repo import RepoMixin
from electronic_inv_sys.infrastructure.db.mongodb.models import (
    MongoDigiKeyProductDetails,
    MongoExistingInventoryItem,
    MongoNewInventoryItem,
    MongoProductOrderInfo,
)
from electronic_inv_sys.util import pydantic_automapper_extend


class MongoInventoryRepo(
    RepoMixin[
        NewInventoryItem,
        ExistingInventoryItem,
        MongoNewInventoryItem,
        MongoExistingInventoryItem,
    ],
    InventoryRepository,
):
    def __init__(self, db: MongoDataDB) -> None:
        mapper = Mapper()
        pydantic_automapper_extend(mapper)
        mapper.add(NewInventoryItem, MongoNewInventoryItem)
        mapper.add(ExistingInventoryItem, MongoExistingInventoryItem)
        mapper.add(MongoExistingInventoryItem, ExistingInventoryItem)
        mapper.add(MongoDigiKeyProductDetails, DigiKeyProductDetails)
        mapper.add(DigiKeyProductDetails, MongoDigiKeyProductDetails)
        mapper.add(ProductOrderInfo, MongoProductOrderInfo)
        mapper.add(MongoProductOrderInfo, ProductOrderInfo)

        collection = db["inventory"]

        collection.create_index(
            [
                ("item_description", "text"),
                ("digikey_part_number", "text"),
                ("manufacturer_part_number", "text"),
                ("comments", "text"),
                ("manufacturer_name", "text"),
                ("product_details.detailed_description", "text"),
            ],
            name="search_index",
            default_language="english",
            weights={
                "item_description": 10,
                "digikey_part_number": 5,
                "manufacturer_part_number": 5,
                "comments": 10,
                "manufacturer_name": 5,
                "product_details.detailed_description": 10,
            },
        )

        super().__init__(
            collection=collection,
            mapper=mapper,
            db_existing_cls=MongoExistingInventoryItem,
        )

    def text_search(
        self, query: str, max_results: int | None = None
    ) -> list[ExistingInventoryItem]:
        result = self._collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}},
            limit=max_results or 0,
        ).sort([("score", {"$meta": "textScore"})])

        output: list[ExistingInventoryItem] = []
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output.append(
                self._mapper.map(
                    item,
                    fields_mapping=self.__field_mapping_from_db(item),
                )
            )
        return output

    def __field_mapping_from_db(
        self, item: MongoExistingInventoryItem
    ) -> dict[str, Any]:
        return {
            "slot_ids": {int(e) for e in item.slot_ids},
            "digikey_barcode_2d": set(item.digikey_barcode_2d),
            "digikey_barcode_1d": set(item.digikey_barcode_1d),
            "_id": item.id,
        }

    def __field_mapping_to_db(
        self, item: ExistingInventoryItem | NewInventoryItem
    ) -> dict[str, Any]:
        common: dict[str, Any] = {
            "slot_ids": {str(k): None for k in item.slot_ids},
            "digikey_barcode_2d": {k: None for k in item.digikey_barcode_2d},
            "digikey_barcode_1d": {k: None for k in item.digikey_barcode_1d},
        }
        if isinstance(item, ExistingInventoryItem):
            common["_id"] = item.id
        return common

    def _db_map_to_contract_existing(
        self, item: MongoExistingInventoryItem
    ) -> ExistingInventoryItem:
        return self._mapper.map(item, fields_mapping=self.__field_mapping_from_db(item))

    def _contract_map_to_db_existing(
        self, item: ExistingInventoryItem
    ) -> MongoExistingInventoryItem:
        return self._mapper.map(item, fields_mapping=self.__field_mapping_to_db(item))

    def _contract_map_to_db_new(self, item: NewInventoryItem) -> MongoNewInventoryItem:
        return self._mapper.map(item, fields_mapping=self.__field_mapping_to_db(item))

    def _item_extra_validation(
        self, item: MongoExistingInventoryItem | MongoNewInventoryItem
    ) -> None:
        if item.digikey_part_number is not None:
            # digikey part number is unique
            possible_match = self.get_item_by_digikey_part_number(
                item.digikey_part_number
            )
            if possible_match is not None:
                if isinstance(item, MongoExistingInventoryItem):
                    if (
                        possible_match.id != item.id
                    ):  # check if just updating the same item
                        raise DuplicateDigiKeyPartNumberError(
                            possible_match.id, item.id
                        )
                else:
                    raise DuplicateDigiKeyPartNumberError(possible_match.id, None)

    def add_to_slot(self, item_id: ObjectId, slot_id: int):
        result = self._collection.update_one(
            {"_id": item_id},
            {"$set": {f"slot_ids.{slot_id}": None}},
        )
        if result.matched_count != 1:
            raise KeyError(f"No item found for key {item_id}")

    def remove_from_slot(self, item_id: ObjectId, slot_id: int):
        slots = self.get_slots_of_item(item_id)
        if slot_id not in slots:
            raise KeyError(f"Item {item_id} not in slot {slot_id}")

        result = self._collection.update_one(
            {"_id": item_id},
            {"$unset": {f"slot_ids.{slot_id}": None}},
        )
        if result.matched_count != 1:
            raise KeyError(f"No item found for key {item_id}")

    def get_slots_of_item(self, item_id: ObjectId) -> set[int]:
        x = self._collection.find_one({"_id": item_id}, {"slot_ids": 1})
        if x is None:
            raise KeyError(f"No item found for key {item_id}")
        return {int(k) for k in x["slot_ids"]}

    def get_item_by_digikey_part_number(
        self, digikey_part_number: str
    ) -> ExistingInventoryItem | None:
        x = self._collection.find_one({"digikey_part_number": digikey_part_number})
        if x is None:
            return None
        item = MongoExistingInventoryItem(**x)
        return self._mapper.map(
            item,
            fields_mapping=self.__field_mapping_from_db(item),
        )

    def get_items_by_manufacturer_part_numbers(
        self, manufacturer_part_numbers: list[str]
    ) -> list[ExistingInventoryItem]:
        if not manufacturer_part_numbers:
            return []

        result = self._collection.find(
            {"manufacturer_part_number": {"$in": manufacturer_part_numbers}}
        )

        return [
            self._db_map_to_contract_existing(MongoExistingInventoryItem(**x))
            for x in result
        ]

    def get_slot(self, slot_id: int) -> list[ExistingInventoryItem]:
        result = self._collection.find({f"slot_ids.{slot_id}": {"$exists": True}})

        output: list[ExistingInventoryItem] = []
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output.append(
                self._mapper.map(
                    item,
                    fields_mapping=self.__field_mapping_from_db(item),
                )
            )
        if not output:
            raise KeyError(f"No items in slot {slot_id}")
        return output
