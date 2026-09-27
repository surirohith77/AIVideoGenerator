import os
import shutil
from typing import BinaryIO
from app.providers.storage.base import StorageProvider
from app.config import settings

class LocalStorageProvider(StorageProvider):
    def __init__(self):
        self.base_dir = os.path.abspath(settings.STORAGE_PATH)
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_file(self, file_obj: BinaryIO, relative_path: str) -> str:
        full_path = os.path.join(self.base_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)
        return full_path

    async def get_file_path(self, relative_path: str) -> str:
        return os.path.join(self.base_dir, relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        full_path = os.path.join(self.base_dir, relative_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
