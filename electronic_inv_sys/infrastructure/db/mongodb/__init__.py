from typing import Any
from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database
from electronic_inv_sys.util import Environment


class MongoDataDB:
    DEV_DB_NAME = "electronic_inv_sys_dev"
    PROD_DB_NAME = "electronic_inv_sys"

    def __init__(self, client: MongoClient[Any], env: Environment) -> None:
        match env:
            case Environment.DEV:
                self.__db = client[MongoDataDB.DEV_DB_NAME]
            case Environment.PROD:
                self.__db = client[MongoDataDB.PROD_DB_NAME]
            case Environment.TEST:
                raise ValueError("Don't use MongoDataDB in test environment")

    def __getitem__(self, name: str) -> Collection[Any]:
        return self.__db[name]

    @property
    def db(self) -> Database[Any]:
        return self.__db
