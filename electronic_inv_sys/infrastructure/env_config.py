from collections.abc import KeysView, ItemsView, Iterator, ValuesView
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING
import dotenv
from loguru import logger

from electronic_inv_sys.contracts.repos import ConfigRepository
from electronic_inv_sys.util import Environment


class EnvConfig(ConfigRepository):
    def __init__(
        self, dotenv_path: str | Path | None = None, env: Environment | None = None
    ):
        self.__config = {
            k: v for k, v in dotenv.dotenv_values(dotenv_path).items() if v is not None
        }
        if env is not None:
            self.__env = env
        else:
            try:
                self.__env = Environment.from_env()
            except KeyError:
                if Environment.var_key() not in self.__config:
                    raise KeyError(
                        f"Environment variable {Environment.var_key()} not found in .env file or environment"
                    )
                self.__env = Environment.from_arg(self.__config[Environment.var_key()])

        # backtrace=False prevents loguru from logging everything, and instead stopping at the try-except block
        logger.configure(handlers=[{"sink": sys.stderr, "backtrace": False}])

    def __iter__(self) -> Iterator[str]:
        return iter(self.__config)

    def __getitem__(self, key: str) -> str:
        if (val := os.environ.get(key)) is not None:
            return val

        return self.__config[key]

    def __len__(self) -> int:
        return len(self.__config)

    def values(self) -> ValuesView[str]:
        return self.__config.values()

    def keys(self) -> KeysView[str]:
        return self.__config.keys()

    def items(self) -> ItemsView[str, str]:
        return super().items()

    @property
    def environment(self) -> Environment:
        return self.__env


if TYPE_CHECKING:
    EnvConfig()
