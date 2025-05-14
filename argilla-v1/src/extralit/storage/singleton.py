import os
from typing import Optional
from extralit.storage.files import FileHandler, StorageType


class FileHandlerSingleton:
    _instance: Optional[FileHandler] = None

    @classmethod
    def get_instance(cls) -> FileHandler:
        if cls._instance is None:
            base_path = os.getenv('BASE_PATH', '/default/path')
            storage_type = os.getenv('STORAGE_TYPE', StorageType.FILE)
            bucket_name = os.getenv('BUCKET_NAME', None)
            cls._instance = FileHandler(base_path, storage_type, bucket_name)

        return cls._instance