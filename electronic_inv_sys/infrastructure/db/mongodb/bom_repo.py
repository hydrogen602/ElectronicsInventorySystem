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

    def _db_map_to_contract_existing(self, item: MongoExistingBom) -> ExistingBom:
        return ExistingBom(
            info_line=item.info_line,
            project=self._mapper.to(ProjectInfo).map(item.project),
            rows=[
                self._mapper.to(BomEntry).map(
                    row,
                    fields_mapping={
                        "inventory_item_mapping_ids": set(
                            row.inventory_item_mapping_ids.keys()
                        )
                    },
                )
                for row in item.rows
            ],
            name=item.name,
            _id=item.id,
        )

    def _contract_map_to_db_existing(self, item: ExistingBom) -> MongoExistingBom:
        return MongoExistingBom(
            info_line=item.info_line,
            project=self._mapper.to(MongoProjectInfo).map(item.project),
            rows=[
                self._mapper.to(MongoBomEntry).map(
                    row,
                    fields_mapping={
                        "inventory_item_mapping_ids": {
                            obj_id: None for obj_id in row.inventory_item_mapping_ids
                        }
                    },
                )
                for row in item.rows
            ],
            name=item.name,
            _id=item.id,
        )

    def _contract_map_to_db_new(self, item: NewBom) -> MongoNewBom:
        return MongoNewBom(
            info_line=item.info_line,
            project=self._mapper.to(MongoProjectInfo).map(item.project),
            rows=[
                self._mapper.to(MongoBomEntry).map(
                    row,
                    fields_mapping={
                        "inventory_item_mapping_ids": {
                            obj_id: None for obj_id in row.inventory_item_mapping_ids
                        }
                    },
                )
                for row in item.rows
            ],
            name=item.name,
        )


if __name__ == "__main__":
    dummy_client = MongoClient[Any](host="localhost", port=27017)
    dummy_db = MongoDataDB(dummy_client, Environment.DEV)
    # Check all abstract methods are implemented (pyright will complain if not)
    _ = MongoBomRepo(dummy_db)
