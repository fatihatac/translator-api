from abc import ABC, abstractmethod
from typing import Optional
from models.schemas import WordDetailData


class BaseCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[WordDetailData]:
        pass

    @abstractmethod
    async def set(self, key: str, value: WordDetailData) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def stats(self) -> dict:
        pass
