from collections.abc import Mapping, MutableMapping
from abc import ABC, abstractmethod

from bson import ObjectId
from loguru import logger

from electronic_inv_sys.contracts.models import (
    ExistingBom,
    DigiKeyProductDetails,
    ExistingInventoryItem,
    NewBom,
    NewInventoryItem,
    WithId,
)
from electronic_inv_sys.util import Environment, JSONValue


class ConfigRepository(ABC, Mapping[str, str]):
    STRICT_ORDER_MATCHING_KEY = "STRICT_ORDER_MATCHING"
    """
    Requires a digikey part number and invoice ID to exist on each import.

    Defaults to false.
    """

    def log_set_vars(self):
        for key in [type(self).STRICT_ORDER_MATCHING_KEY]:
            logger.info(
                "{}: {}",
                key,
                self.get(key, None),
            )

    @property
    @abstractmethod
    def environment(self) -> Environment: ...

    def get_as_bool(self, key: str, default: bool | None = None) -> bool:
        try:
            val = self[key]
        except KeyError:
            if default is not None:
                return default
            raise
        val = val.strip().lower()
        match val:
            case "true":
                return True
            case "false":
                return False
            case "yes":
                return True
            case "no":
                return False
            case "1":
                return True
            case "0":
                return False
            case _:
                raise ValueError(f"Invalid boolean value: {val}")


class MetadataRepository(ABC, MutableMapping[str, JSONValue]):
    pass


class DuplicateDigiKeyPartNumberError(Exception):
    """
    When two different db entries (would) have the same digikey part number.
    """

    def __init__(
        self, existing_id: ObjectId, new_id: ObjectId | None, *args: object
    ) -> None:
        self.existing_id = existing_id
        self.new_id = new_id
        super().__init__(f"Item.ids: '{existing_id}' vs '{new_id}'", *args)


class CRUDRepository[N, E: WithId](ABC, MutableMapping[ObjectId, E]):
    """
    'N' is the type of the new item, 'E' is the type of the existing item.
    """

    @abstractmethod
    def add_new(self, item: N) -> ObjectId:
        """
        Add a new item to the repository.
        """
        ...

    def set_existing_item(self, item: E) -> None:
        """Update an existing item in the repository."""
        self.__setitem__(item.id, item)


class InventoryRepository(CRUDRepository[NewInventoryItem, ExistingInventoryItem]):
    """
    Overwrite these for efficiency:
      keys, items, values, set_comments, set_quantity, set_product_details,
      get_item_by_digikey_part_number, assign_to_slot, get_slot
    """

    @abstractmethod
    def text_search(
        self, query: str, max_results: int | None = None
    ) -> list[ExistingInventoryItem]:
        """
        Search the inventory for items that match the query.

        Args:
            query (str): The query to search for.
        Returns:
            list[ExistingInventoryItem]: The items that match the query.
        """

    def add_to_slot(self, item_id: ObjectId, slot_id: int):
        """
        Add an item to a slot in the inventory.

        Args:
            item_id (ObjectId): The ID of the item to assign.
            slot_id (int): The ID of the slot to assign the item to.
        Raises:
            KeyError: If the item ID is not found in the inventory.
        """
        old_item = self[item_id]
        old_item_data = old_item.model_dump(by_alias=True)
        del old_item_data["slot_ids"]
        new_item = ExistingInventoryItem(
            **old_item_data, slot_ids=old_item.slot_ids | {slot_id}
        )
        self.set_existing_item(new_item)

    def remove_from_slot(self, item_id: ObjectId, slot_id: int):
        """
        Remove an item from a slot in the inventory.

        Args:
            item_id (ObjectId): The ID of the item to remove.
            slot_id (int): The ID of the slot to remove the item from.
        Raises:
            KeyError: If the item ID is not found in the inventory.
            KeyError: If the item is not in the specified slot.
        """
        old_item = self[item_id]
        old_item_data = old_item.model_dump(by_alias=True)
        del old_item_data["slot_ids"]

        if slot_id not in old_item.slot_ids:
            raise KeyError(f"Item {item_id} not in slot {slot_id}")

        new_item = ExistingInventoryItem(
            **old_item_data, slot_ids=old_item.slot_ids - {slot_id}
        )
        self.set_existing_item(new_item)

    def get_slots_of_item(self, item_id: ObjectId) -> set[int]:
        """
        Get the slots of an item in the inventory.

        Args:
            item_id (ObjectId): The ID of the item to retrieve.
        Returns:
            set[int]: The slots of the item.
        Raises:
            KeyError: If the item ID is not found in the inventory.
        """
        return self[item_id].slot_ids

    def get_slot(self, slot_id: int) -> list[ExistingInventoryItem]:
        """
        Get the inventory item(s) with the specified slot ID.

        Args:
            slot_id (int): The ID of the slot to retrieve.
        Returns:
            list[InventoryItemV3]: The items in that slot.
        Raises:
            KeyError: If no items are found in that slot ID.
        """
        ls: list[ExistingInventoryItem] = []
        for item in self.values():
            if slot_id in item.slot_ids:
                ls.append(item)

        if not ls:
            raise KeyError(f"No items in slot {slot_id}")
        return ls

    def get_item_by_digikey_part_number(
        self, digikey_part_number: str
    ) -> ExistingInventoryItem | None:
        """
        Get the inventory item with the specified DigiKey part number.

        Args:
            digikey_part_number (str): The DigiKey part number to retrieve.
        Returns:
            ExistingInventoryItem: The item with that part number.
        """
        for item in self.values():
            if item.digikey_part_number == digikey_part_number:
                return item
        return None

    def set_comments(self, id_: ObjectId, comments: str) -> None:
        """
        Sets the comments of an inventory item.

        Args:
            id_ (ObjectId): The ID of the inventory item to update.
            comments (str): The comments to set for the inventory item.

        Raises:
            KeyError: If the specified ID is not found in the inventory.
        """
        item_data = self[id_].model_dump(by_alias=True)
        del item_data["comments"]
        item = ExistingInventoryItem(**item_data, comments=comments)
        self.set_existing_item(item)

    def set_quantity(self, id_: ObjectId, quantity: int) -> None:
        """
        Sets the quantity of an inventory item.

        Args:
            id_ (ObjectId): The ID of the inventory item to update.
            quantity (int): The quantity to set for the inventory item.

        Raises:
            KeyError: If the specified ID is not found in the inventory.
        """
        item_data = self[id_].model_dump(by_alias=True)
        del item_data["available_quantity"]
        item = ExistingInventoryItem(**item_data, available_quantity=quantity)
        self.set_existing_item(item)

    def set_product_details(
        self, id_: ObjectId, product_details: DigiKeyProductDetails
    ) -> None:
        """
        Sets the product details of an inventory item.

        Args:
            id_ (ObjectId): The ID of the inventory item to update.
            product_details (ProductDetails): The product details to set for the inventory item.

        Raises:
            KeyError: If the specified ID is not found in the inventory.
        """
        item_data = self[id_].model_dump(by_alias=True)
        del item_data["product_details"]
        item = ExistingInventoryItem(**item_data, product_details=product_details)
        self.set_existing_item(item)


class BomRepository(CRUDRepository[NewBom, ExistingBom]):
    """Repository for storing and retrieving BOMs."""
