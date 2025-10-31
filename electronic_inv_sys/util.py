from collections.abc import Iterable
from enum import Enum
import os
from typing import Type

import Levenshtein
from automapper import Mapper  # type: ignore
from pydantic import BaseModel

type JSONValue = str | int | float | bool | None | dict[str, JSONValue] | list[
    JSONValue
]


def otl[T](val: T | None) -> list[T]:
    """
    Optional to list
    """
    return [] if val is None else [val]


def ots[T](val: T | None) -> set[T]:
    """
    Optional to set
    """
    return set() if val is None else {val}


class Environment(Enum):
    PROD = "prod"
    DEV = "dev"
    TEST = "test"

    @classmethod
    def var_key(cls) -> str:
        return "ENV"

    @classmethod
    def from_env(cls):
        """
        Valid options:
        ENV=prod
        ENV=dev
        ENV=test

        Raises:
            KeyError: If the environment variable is not set.
            ValueError: If the environment variable is invalid
        """
        return Environment.from_arg(os.environ[cls.var_key()])

    @staticmethod
    def from_arg(arg: str):
        """
        Valid options:
          prod
          dev
          test
        """
        match arg.lower().strip():
            case "prod":
                return Environment.PROD
            case "dev":
                return Environment.DEV
            case "test":
                return Environment.TEST
            case other:
                raise ValueError(f"Invalid environment: {other}")


def pydantic_spec_function(target_cls: Type[BaseModel]) -> Iterable[str]:
    """
    The built-in pydantic for py-automapper has some issues with aliasing.
    This function is a workaround for that.
    """
    return (
        metadata.alias if metadata.alias else field_name
        for field_name, metadata in getattr(target_cls, "model_fields").items()
    )


def pydantic_automapper_extend(mapper: Mapper) -> None:
    mapper.add_spec(BaseModel, pydantic_spec_function)


def relatively_similar(a: str, b: str) -> bool:
    """
    Returns True if the two strings are kinda the same.
    """
    a = a.lower().strip()
    b = b.lower().strip()
    # simplify whitespace
    a = " ".join(a.split())
    b = " ".join(b.split())
    # remove non-alphanumeric characters like punctuation
    a = "".join(c for c in a if c.isalnum() or c == " ")
    b = "".join(c for c in b if c.isalnum() or c == " ")
    return (
        Levenshtein.ratio(a, b) >= 0.5
    )  # welp each manufacurer has several similar names, e.g 'WURTH ELECTRONICS INC (VA)' vs 'Würth Elektronik'
