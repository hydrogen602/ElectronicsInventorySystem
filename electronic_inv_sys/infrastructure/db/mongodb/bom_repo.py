from __future__ import annotations

from typing import Any
from pymongo import MongoClient
from automapper import Mapper  # pyright: ignore[reportMissingTypeStubs]

from electronic_inv_sys.contracts.models import (
    ExistingBom,
    BomEntry,
    FusionBomEntry,
    NewBom,
    ProjectInfo,
)
from electronic_inv_sys.contracts.repos import BomRepository
from electronic_inv_sys.infrastructure.db.mongodb import MongoDataDB
from electronic_inv_sys.infrastructure.db.mongodb.mixin import RepoMixin
from electronic_inv_sys.infrastructure.db.mongodb.models import (
    MongoBomEntry,
    MongoExistingBom,
    MongoFusionBomEntry,
    MongoNewBom,
    MongoProjectInfo,
)
from electronic_inv_sys.util import Environment, pydantic_automapper_extend


class MongoBomRepo(
    RepoMixin[NewBom, ExistingBom, MongoNewBom, MongoExistingBom], BomRepository
):
    def __init__(self, db: MongoDataDB) -> None:
        mapper = Mapper()
        pydantic_automapper_extend(mapper)
        mapper.add(NewBom, MongoNewBom)
        mapper.add(ExistingBom, MongoExistingBom)
        mapper.add(MongoExistingBom, ExistingBom)
        mapper.add(BomEntry, MongoBomEntry)
        mapper.add(MongoBomEntry, BomEntry)
        mapper.add(FusionBomEntry, MongoFusionBomEntry)
        mapper.add(MongoFusionBomEntry, FusionBomEntry)
        mapper.add(ProjectInfo, MongoProjectInfo)
        mapper.add(MongoProjectInfo, ProjectInfo)

        super().__init__(
            collection=db["boms"], mapper=mapper, db_existing_cls=MongoExistingBom
        )


if __name__ == "__main__":
    dummy_client = MongoClient[Any](host="localhost", port=27017)
    dummy_db = MongoDataDB(dummy_client, Environment.DEV)
    # Check all abstract methods are implemented (pyright will complain if not)
    _ = MongoBomRepo(dummy_db)
