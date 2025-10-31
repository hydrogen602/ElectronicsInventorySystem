from collections.abc import ItemsView, Iterator, KeysView, ValuesView
from typing import Any
from bson.objectid import ObjectId
from loguru import logger
from pymongo import MongoClient
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
from electronic_inv_sys.infrastructure.db.mongodb.models import (
    MongoDigiKeyProductDetails,
    MongoExistingInventoryItem,
    MongoNewInventoryItem,
    MongoProductOrderInfo,
)
from electronic_inv_sys.util import Environment, pydantic_automapper_extend


class MongoInventoryRepo(InventoryRepository):
    def __init__(self, client: MongoClient[Any], env: Environment) -> None:
        self.__mapper = Mapper()
        pydantic_automapper_extend(self.__mapper)
        self.__mapper.add(NewInventoryItem, MongoNewInventoryItem)
        self.__mapper.add(ExistingInventoryItem, MongoExistingInventoryItem)
        self.__mapper.add(MongoExistingInventoryItem, ExistingInventoryItem)
        self.__mapper.add(MongoDigiKeyProductDetails, DigiKeyProductDetails)
        self.__mapper.add(DigiKeyProductDetails, MongoDigiKeyProductDetails)
        self.__mapper.add(ProductOrderInfo, MongoProductOrderInfo)
        self.__mapper.add(MongoProductOrderInfo, ProductOrderInfo)

        match env:
            case Environment.DEV:
                db = client["electronic_inv_sys_dev"]
                logger.info("Using dev database")
            case Environment.PROD:
                db = client["electronic_inv_sys"]
                logger.info("Using prod database")
            case Environment.TEST:
                raise ValueError("Don't use MongoInventoryRepo in test environment")

        self.__collection = db["inventory"]

        self.__collection.create_index(
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

    def text_search(
        self, query: str, max_results: int | None = None
    ) -> list[ExistingInventoryItem]:
        result = self.__collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}},
            limit=max_results or 0,
        ).sort([("score", {"$meta": "textScore"})])

        output: list[ExistingInventoryItem] = []
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output.append(
                self.__mapper.map(
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

    def __getitem__(self, key: ObjectId) -> ExistingInventoryItem:
        x = self.__collection.find_one({"_id": key})
        if x is None:
            raise KeyError(f"No item found for key {key}")
        item = MongoExistingInventoryItem(**x)
        return self.__mapper.map(
            item,
            fields_mapping=self.__field_mapping_from_db(item),
        )

    def __iter__(self) -> Iterator[ObjectId]:
        return iter(self.__collection.find({}, {"_id": 1}))

    def __len__(self) -> int:
        return self.__collection.count_documents({})

    def set_existing_item(self, item: ExistingInventoryItem) -> None:
        if item.digikey_part_number is not None:
            possible_match = self.get_item_by_digikey_part_number(
                item.digikey_part_number
            )
            if possible_match is not None and possible_match.id != item.id:
                raise DuplicateDigiKeyPartNumberError(possible_match.id, item.id)

        if self.__collection.find_one({"_id": item.id}) is None:
            raise KeyError(
                f"Item with ID {item.id} not found in inventory. Keys should be generated by the DB, not the user."
            )

        db_item: MongoExistingInventoryItem = self.__mapper.map(
            item, fields_mapping=self.__field_mapping_to_db(item)
        )

        # we need the id field to show up as _id for MongoDB
        result = self.__collection.replace_one(
            {"_id": item.id}, db_item.model_dump(by_alias=True)
        )
        if result.matched_count != 1:
            raise RuntimeError(
                f"Item with ID {item.id} not found in inventory - but we just checked!"
            )

    def add_new_item(self, item: NewInventoryItem) -> ObjectId:
        if item.digikey_part_number is not None:
            possible_match = self.get_item_by_digikey_part_number(
                item.digikey_part_number
            )
            if possible_match is not None:
                raise DuplicateDigiKeyPartNumberError(possible_match.id, None)

        db_item: MongoNewInventoryItem = self.__mapper.map(
            item, fields_mapping=self.__field_mapping_to_db(item)
        )

        # MongoNewInventoryItem doesn't have an id field, so we don't need by_alias=True
        result = self.__collection.insert_one(db_item.model_dump())
        return result.inserted_id

    def add_to_slot(self, item_id: ObjectId, slot_id: int):
        result = self.__collection.update_one(
            {"_id": item_id},
            {"$set": {f"slot_ids.{slot_id}": None}},
        )
        if result.matched_count != 1:
            raise KeyError(f"No item found for key {item_id}")

    def remove_from_slot(self, item_id: ObjectId, slot_id: int):
        slots = self.get_slots_of_item(item_id)
        if slot_id not in slots:
            raise KeyError(f"Item {item_id} not in slot {slot_id}")

        result = self.__collection.update_one(
            {"_id": item_id},
            {"$unset": {f"slot_ids.{slot_id}": None}},
        )
        if result.matched_count != 1:
            raise KeyError(f"No item found for key {item_id}")

    def get_slots_of_item(self, item_id: ObjectId) -> set[int]:
        x = self.__collection.find_one({"_id": item_id}, {"slot_ids": 1})
        if x is None:
            raise KeyError(f"No item found for key {item_id}")
        return {int(k) for k in x["slot_ids"]}

    def get_item_by_digikey_part_number(
        self, digikey_part_number: str
    ) -> ExistingInventoryItem | None:
        x = self.__collection.find_one({"digikey_part_number": digikey_part_number})
        if x is None:
            return None
        item = MongoExistingInventoryItem(**x)
        return self.__mapper.map(
            item,
            fields_mapping=self.__field_mapping_from_db(item),
        )

    def get_slot(self, slot_id: int) -> list[ExistingInventoryItem]:
        result = self.__collection.find({f"slot_ids.{slot_id}": {"$exists": True}})

        output: list[ExistingInventoryItem] = []
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output.append(
                self.__mapper.map(
                    item,
                    fields_mapping=self.__field_mapping_from_db(item),
                )
            )
        if not output:
            raise KeyError(f"No items in slot {slot_id}")
        return output

    def keys(self) -> KeysView[ObjectId]:
        return set(e["_id"] for e in self.__collection.find({}, {"_id": 1}))  # type: ignore

    def values(self) -> ValuesView[ExistingInventoryItem]:
        result = self.__collection.find({})
        output: list[ExistingInventoryItem] = []
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output.append(
                self.__mapper.map(
                    item,
                    fields_mapping=self.__field_mapping_from_db(item),
                )
            )
        return output  # type: ignore

    def items(self) -> ItemsView[ObjectId, ExistingInventoryItem]:
        result = self.__collection.find({})
        output: dict[ObjectId, ExistingInventoryItem] = {}
        for x in result:
            item = MongoExistingInventoryItem(**x)
            output[item.id] = self.__mapper.map(
                item,
                fields_mapping=self.__field_mapping_from_db(item),
            )
        return output.items()
