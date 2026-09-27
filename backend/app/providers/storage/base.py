from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageProvider(ABC):
    @abstractmethod
    async def save_file(self, file_obj: BinaryIO, relative_path: str) -> str:
        pass

    @abstractmethod
    async def get_file_path(self, relative_path: str) -> str:
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        pass
