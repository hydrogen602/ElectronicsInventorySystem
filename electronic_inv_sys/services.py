from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Self
import httpx
from loguru import logger
from pymongo import MongoClient

from electronic_inv_sys.contracts.repos import (
    InventoryRepository,
    ConfigRepository,
    MetadataRepository,
)
from electronic_inv_sys.contracts.digikey_api import DigiKeyAPI
from electronic_inv_sys.infrastructure.db.mongodb.inventory_repo import (
    MongoInventoryRepo,
)
from electronic_inv_sys.infrastructure.db.mongodb.metadata_repo import MongoMetadataRepo
from electronic_inv_sys.infrastructure.env_config import EnvConfig
from electronic_inv_sys.infrastructure.digikey_api import DigiKeyAPIImpl
from electronic_inv_sys.logic.bom import BomAnalysis


@dataclass
class Services:
    inventory: InventoryRepository
    config: ConfigRepository
    metadata: MetadataRepository
    digikey_api: DigiKeyAPI
    bom: BomAnalysis

    def summary_of_implementations(self) -> str:
        return (
            "\n"
            f"  inventory:   {type(self.inventory).__name__}\n"
            f"  config:      {type(self.config).__name__}\n"
            f"  metadata:    {type(self.metadata).__name__}\n"
            f"  digikey_api: {type(self.digikey_api).__name__}"
        )


@asynccontextmanager
async def services_factory(config: EnvConfig):
    conn = config["MONGO_CONN"]

    mongo_client: MongoClient[Any]
    # with requests.Session() as session, MongoClient(conn) as mongo_client:
    with MongoClient(conn) as mongo_client:
        async with httpx.AsyncClient() as session:
            metadata = MongoMetadataRepo(mongo_client, config.environment)
            inventory = MongoInventoryRepo(mongo_client, config.environment)

            services = Services(
                inventory=inventory,
                config=config,
                metadata=metadata,
                digikey_api=DigiKeyAPIImpl(session, metadata, config),
                bom=BomAnalysis(inventory),
            )
            yield services


class ServicesProviderSingleton:
    __instance: Self | None = None

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if cls.__instance is None:
            logger.info("args: {}, cls: {}", args, cls)
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, services: Services) -> None:
        logger.info(
            "Initializing ServicesProviderSingleton with services: {}",
            services.summary_of_implementations(),
        )
        self.__services = services

    @classmethod
    def services(cls) -> Services:
        return cls.instance().__services

    @classmethod
    def delete_instance(cls) -> None:
        cls.__instance = None

    @classmethod
    def instance(cls) -> Self:
        if cls.__instance is None:
            raise RuntimeError("ServicesProviderSingleton not yet initialized")
        return cls.__instance
