import json
from pathlib import Path

from electronic_inv_sys.contracts.repos import MetadataRepository
from electronic_inv_sys.util import JSONValue


class MetadataFileStore(MetadataRepository):
    def __init__(self, path: Path | str = ".env.json"):
        self.__path = Path(path)
        with self.__path.open() as f:
            self.__local_copy = json.load(f)

    def __getitem__(self, key: str) -> JSONValue:
        return self.__local_copy[key]

    def __setitem__(self, key: str, value: JSONValue) -> None:
        self.__local_copy[key] = value
        with self.__path.open("w") as f:
            json.dump(self.__local_copy, f)

    def __delitem__(self, key: str) -> None:
        del self.__local_copy[key]
        with self.__path.open("w") as f:
            json.dump(self.__local_copy, f)

    def __iter__(self):
        return iter(self.__local_copy)

    def __len__(self) -> int:
        return len(self.__local_copy)

    def keys(self):
        return self.__local_copy.keys()

    def items(self):
        return self.__local_copy.items()

    def values(self):
        return self.__local_copy.values()
