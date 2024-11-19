from enum import Enum
import os
import json
import dill
import pandas as pd
from typing import Optional, Tuple
from minio import Minio
from minio.error import S3Error
import fsspec

from extralit.server.context.files import get_minio_client


class StorageType(Enum):
    FILE = 'file'
    S3 = 's3'
    

class FileHandler:
    def __init__(self, base_path: str, storage_type: StorageType = StorageType.FILE, bucket_name: Optional[str] = None):
        self.base_path = base_path
        self.storage_type = storage_type
        self.bucket_name = bucket_name

        if storage_type == StorageType.S3:
            assert bucket_name is not None
            self.client = get_minio_client()

    def _get_full_path(self, path: str) -> str:
        return os.path.join(self.base_path, path)

    def exists(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            return os.path.exists(full_path)
        
        elif self.storage_type.value == StorageType.S3.value:
            try:
                self.client.stat_object(self.bucket_name, full_path)
                return True
            except S3Error:
                return False

        return False

    def read_json(self, path: str) -> dict:
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            with open(full_path, 'r') as file:
                return json.load(file)
            
        elif self.storage_type.value == StorageType.S3.value:
            response = self.client.get_object(self.bucket_name, full_path)
            return json.loads(response.read().decode('utf-8'))

    def write_json(self, path: str, data: dict):
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as file:
                json.dump(data, file)

        elif self.storage_type.value == StorageType.S3.value:
            self.client.put_object(self.bucket_name, full_path, json.dumps(data).encode('utf-8'), len(json.dumps(data)))

    def read_dill(self, path: str):
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            with open(full_path, 'rb') as file:
                return dill.load(file)
            
        elif self.storage_type.value == StorageType.S3.value:
            response = self.client.get_object(self.bucket_name, full_path)
            return dill.loads(response.read())

    def write_dill(self, path: str, data):
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as file:
                dill.dump(data, file)

        elif self.storage_type.value == StorageType.S3.value:
            self.client.put_object(self.bucket_name, full_path, dill.dumps(data), len(dill.dumps(data)))

    def read_text(self, path: str) -> str:
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            with open(full_path, 'r') as file:
                return file.read()
            
        elif self.storage_type.value == StorageType.S3.value:
            response = self.client.get_object(self.bucket_name, full_path)
            return response.read().decode('utf-8')

    def write_text(self, path: str, data: str):
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as file:
                file.write(data)

        elif self.storage_type.value == StorageType.S3.value:
            self.client.put_object(self.bucket_name, full_path, data.encode('utf-8'), len(data))

    def delete(self, path: str):
        full_path = self._get_full_path(path)
        if self.storage_type.value == StorageType.FILE.value:
            if os.path.exists(full_path):
                os.remove(full_path)
            else:
                raise FileNotFoundError(f"The file {full_path} does not exist.")
        
        elif self.storage_type.value == StorageType.S3.value:
            try:
                self.client.remove_object(self.bucket_name, full_path)
            except S3Error as e:
                raise FileNotFoundError(f"The object {full_path} does not exist in bucket {self.bucket_name}.") from e