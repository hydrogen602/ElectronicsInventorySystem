from typing import Any, TypedDict
from collections.abc import ItemsView, KeysView, Iterator, ValuesView

from pymongo import MongoClient
from pymongo.collection import Collection

from electronic_inv_sys.contracts.repos import MetadataRepository
from electronic_inv_sys.util import Environment, JSONValue


class MongoMetadataRepo(MetadataRepository):
    class _KeyValue(TypedDict):
        key: str
        value: JSONValue

    def __init__(self, client: MongoClient[Any], env: Environment) -> None:
        match env:
            case Environment.DEV:
                db = client["metadata"]
            case Environment.PROD:
                db = client["metadata"]
            case Environment.TEST:
                raise ValueError("Don't use MongoMetadataRepo in test environment")

        self.__collection: Collection[MongoMetadataRepo._KeyValue] = db["cfg"]

    def __getitem__(self, key: str) -> JSONValue:
        """
        Retrieve the value associated with the given key from the database.

        Args:
            key (str): The key to retrieve the value for.
        Returns:
            Any: The value associated with the given key.
        Raises:
            TypeError: If the key is not a string.
            KeyError: If no value is found for the given key.
        """

        if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Key must be a string")
        val = self.__collection.find_one({"key": key}, {"value": 1})
        if val is None:
            raise KeyError(f"No value found for key {key}")
        return val["value"]

    def __setitem__(self, key: str, value: JSONValue) -> None:
        """
        Update the value of an item in the database.
        The key must already exist in the database.

        Args:
            key (str): The key of the item.
            value (Any): The value to be set.
        Raises:
            TypeError: If the key is not a string.
            KeyError: If the key is not already present.
        """

        if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Key must be a string")

        result = self.__collection.update_one(
            {"key": key},
            {"$set": {"value": value}},
        )
        if result.matched_count == 0:
            raise KeyError(f"No key found for update with key {key}")

    def __delitem__(self, key: str) -> None:
        """
        Remove an item from the database.

        Args:
            key (str): The key of the item to remove.
        Raises:
            TypeError: If the key is not a string.
            KeyError: If the key is not found.
        """

        if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("Key must be a string")

        result = self.__collection.delete_one({"key": key})
        if result.deleted_count == 0:
            raise KeyError(f"No key found for deletion with key {key}")

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over the keys in the database.

        Returns:
            Iterator[str]: An iterator over the keys in the database.
        """

        return map(lambda x: x["key"], self.__collection.find({}, {"key": 1}))

    def __len__(self) -> int:
        """
        Get the number of items in the database.

        Returns:
            int: The number of items in the database.
        """

        return self.__collection.count_documents({})

    def keys(self) -> KeysView[str]:
        return {x["key"] for x in self.__collection.find({}, {"key": 1})}  # type: ignore

    def values(self) -> ValuesView[JSONValue]:
        return [x["value"] for x in self.__collection.find({}, {"value": 1})]  # type: ignore

    def items(self) -> ItemsView[str, JSONValue]:
        return [  # type: ignore
            (x["key"], x["value"])
            for x in self.__collection.find({}, {"key": 1, "value": 1})
        ]
