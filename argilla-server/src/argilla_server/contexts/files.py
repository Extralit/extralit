import io
import shutil
import json
import hashlib
import uuid
import logging  
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union, Iterator
from urllib.parse import urlparse
from uuid import UUID

from argilla_server.api.schemas.v1.files import ListObjectsResponse, ObjectMetadata, FileObjectResponse
from argilla_server.settings import settings
from fastapi import HTTPException
from minio import Minio, S3Error
from minio.helpers import ObjectWriteResult
from minio.versioningconfig import VersioningConfig
from minio.commonconfig import ENABLED
from minio.datatypes import Object

EXCLUDED_VERSIONING_PREFIXES = ['pdf']

_LOGGER = logging.getLogger("argilla")


class LocalFileStorage:
    """Local file storage implementation that mimics Minio client interface."""
    
    def __init__(self, base_dir: Union[str, Path]):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_bucket_path(self, bucket_name: str) -> Path:
        bucket_path = self.base_dir / bucket_name
        return bucket_path
        
    def _get_object_path(self, bucket_name: str, object_name: str) -> Path:
        bucket_path = self._get_bucket_path(bucket_name)
        object_path = bucket_path / object_name
        return object_path
    
    def _get_version_path(self, bucket_name: str, object_name: str) -> Path:
        bucket_path = self._get_bucket_path(bucket_name)
        version_path = bucket_path / ".versions" / object_name
        return version_path
    
    def make_bucket(self, bucket_name: str) -> None:
        bucket_path = self._get_bucket_path(bucket_name)
        bucket_path.mkdir(parents=True, exist_ok=True)
        # Create versions directory
        (bucket_path / ".versions").mkdir(exist_ok=True)
        
    def set_bucket_versioning(self, bucket_name: str, config: Any) -> None:
        # Just create the versions directory
        bucket_path = self._get_bucket_path(bucket_name)
        (bucket_path / ".versions").mkdir(exist_ok=True)
    
    def bucket_exists(self, bucket_name: str) -> bool:
        bucket_path = self._get_bucket_path(bucket_name)
        return bucket_path.exists() and bucket_path.is_dir()
    
    def put_object(self, bucket_name: str, object_name: str, data: Union[BinaryIO, bytes], 
                  length: Optional[int] = None, content_type: Optional[str] = None,
                  part_size: int = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        # Ensure bucket exists
        bucket_path = self._get_bucket_path(bucket_name)
        bucket_path.mkdir(parents=True, exist_ok=True)

        if not isinstance(data, bytes):
            data_bytes = data.read()
        else:
            data_bytes = data

        # Generate content-based version ID and ETag
        content_hash = compute_hash(data_bytes)
        version_id = str(uuid.uuid4())

        version_path = self._get_version_path(bucket_name, object_name).with_suffix(f'.{version_id}')
        version_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write data to version file
        with open(version_path, 'wb') as f:
            f.write(data_bytes)

        object_path = self._get_object_path(bucket_name, object_name)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            object_path.unlink()  # Remove existing file/symlink
        object_path.symlink_to(version_path)

        # Always write metadata with content hash
        meta_path = object_path.with_suffix('.metadata.json')
        metadata = metadata or {}
        metadata.update({
            "etag": content_hash,
            "content_type": content_type or "application/octet-stream",
            "version_id": version_id
        })
        with open(meta_path, 'w') as f:
            json.dump(metadata, f)
        
        return {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "version_id": version_id,
            "etag": content_hash,
            "size": len(data_bytes)
        }
    
    def get_object(self, bucket_name: str, object_name: str, version_id: Optional[str] = None) -> io.BytesIO:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f'.{version_id}')
            if not version_path.exists():
                raise S3Error("NoSuchKey", "The specified version does not exist", resource=object_name)
            with open(version_path, 'rb') as f:
                return io.BytesIO(f.read())
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise S3Error("NoSuchKey", "The specified key does not exist", resource=object_name)
            with open(object_path, 'rb') as f:
                return io.BytesIO(f.read())
    
    def stat_object(self, bucket_name: str, object_name: str, version_id: Optional[str] = None) -> Dict[str, Any]:
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f'.{version_id}')
            if not version_path.exists():
                raise S3Error("NoSuchKey", "The specified version does not exist", resource=object_name)
            path = version_path
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if not object_path.exists():
                raise S3Error("NoSuchKey", "The specified key does not exist", resource=object_name)
            path = object_path
        
        # Get metadata from file
        meta_path = self._get_object_path(bucket_name, object_name).with_suffix('.metadata.json')
        if not meta_path.exists():
            raise S3Error("NoSuchKey", "The specified key does not exist", resource=object_name)
            
        with open(meta_path, 'r') as f:
            metadata = json.load(f)
        
        stats = path.stat()
        return {
            "bucket_name": bucket_name,
            "object_name": object_name,
            "version_id": version_id or metadata.get("version_id"),
            "etag": metadata.get("etag"),
            "size": stats.st_size,
            "last_modified": stats.st_mtime,
            "metadata": metadata,
            "content_type": metadata.get("content_type", "application/octet-stream")
        }
    
    def remove_object(self, bucket_name: str, object_name: str, version_id: Optional[str] = None):
        if version_id:
            version_path = self._get_version_path(bucket_name, object_name).with_suffix(f'.{version_id}')
            if version_path.exists():
                version_path.unlink()
        else:
            object_path = self._get_object_path(bucket_name, object_name)
            if object_path.exists():
                object_path.unlink()
                
                # Remove metadata if exists
                meta_path = object_path.with_suffix('.metadata.json')
                if meta_path.exists():
                    meta_path.unlink()
    
    def list_objects(self, bucket_name: str, prefix: Optional[str] = None, 
                    recursive: bool = False, include_version: bool = False,
                    start_after: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        bucket_path = self._get_bucket_path(bucket_name)
        if not bucket_path.exists():
            raise S3Error("NoSuchBucket", "The specified bucket does not exist", resource=bucket_name)
        
        # Get all files in bucket (and subdirectories if recursive)
        pattern = "**/*" if recursive else "*"
        files = list(bucket_path.glob(pattern))
        
        # Filter by prefix if provided
        if prefix:
            files = [f for f in files if str(f.relative_to(bucket_path)).startswith(prefix)]
        
        # Filter out directories and metadata files
        files = [f for f in files if f.is_file() and not f.name.endswith('.metadata.json') and '.versions' not in str(f)]
        
        # Sort by name
        files.sort()
        
        # Apply start_after if provided
        if start_after:
            files = [f for f in files if str(f.relative_to(bucket_path)) > start_after]
        
        # Convert to objects
        for file_path in files:
            object_name = str(file_path.relative_to(bucket_path))
            stats = file_path.stat()
            
            # Get metadata from file
            meta_path = file_path.with_suffix('.metadata.json')
            if not meta_path.exists():
                continue  # Skip objects without metadata
                
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            obj = {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "is_dir": False,
                "etag": metadata.get("etag"),
                "size": stats.st_size,
                "last_modified": stats.st_mtime,
                "metadata": metadata,
                "content_type": metadata.get("content_type", "application/octet-stream")
            }
            
            if include_version:
                obj["version_id"] = metadata.get("version_id")
            
            yield obj


def get_minio_client() -> Optional[Union[Minio, LocalFileStorage]]:
    if None in [settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]:
        # Use local file storage instead
        local_storage_path = settings.home_path / "local_storage"
        _LOGGER.info(f"Using local file storage at: {local_storage_path}")
        return LocalFileStorage(local_storage_path)

    try:
        parsed_url = urlparse(settings.s3_endpoint)
        hostname = parsed_url.hostname
        port = parsed_url.port

        if hostname is None:
            print(f"Invalid URL: no hostname found, possible due to lacking http(s) protocol. Given '{settings.s3_endpoint}'")
            return None

        return Minio(
            endpoint=f'{hostname}:{port}' if port else hostname,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=parsed_url.scheme == "https",
        )
    except Exception as e:
        _LOGGER.error(f"Error creating Minio client: {e}", stack_info=True)
        raise e


def compute_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def get_pdf_s3_object_path(id: Union[UUID, str]) -> str:
    if not id:
        raise Exception("id cannot be None")
    
    elif isinstance(id, UUID):
        object_path = f'pdf/{str(id)}'
    else:
        object_path = f'pdf/{id}'

    return object_path


def get_s3_object_url(bucket_name: str, object_path: str) -> str:
    return f'/api/v1/file/{bucket_name}/{object_path}'


def list_objects(client: Union[Minio, LocalFileStorage], bucket: str, prefix: Optional[str] = None, include_version=True, recursive=True, start_after: Optional[str]=None) -> ListObjectsResponse:
    objects = client.list_objects(bucket, prefix=prefix, recursive=recursive, include_version=include_version, start_after=start_after)
    objects = [ObjectMetadata.from_minio_object(obj) for obj in objects]
    return ListObjectsResponse(objects=objects)

def get_object(client: Union[Minio, LocalFileStorage], bucket: str, object: str, version_id: Optional[str] = None, 
               include_versions=False) -> FileObjectResponse:
    try:
        stat = client.stat_object(bucket, object, version_id=version_id)
    except S3Error as se:
        if version_id:
            _LOGGER.warning(f"Error getting object {object} from bucket {bucket} with version {version_id}: {se}")
            try:
                _LOGGER.info(f"Retrying without version_id for object {object} in bucket {bucket}")
                stat = client.stat_object(bucket, object)
            except S3Error as se_retry:
                raise se_retry
        else:
            raise se

    try:
        obj = client.get_object(bucket, object, version_id=stat.version_id)

        if include_versions:
            versions = list_objects(client, bucket, prefix=object, include_version=include_versions)
        else:
            versions = None

        return FileObjectResponse(response=obj, metadata=stat, versions=versions)
    
    except S3Error as se:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {se}")
        raise HTTPException(status_code=404, detail=f"Object {object} not found in bucket {bucket}")
    except Exception as e:
        _LOGGER.error(f"Error getting object {object} from bucket {bucket}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e.message}")
    

def put_object(client: Union[Minio, LocalFileStorage], bucket: str, object: str, data: Union[BinaryIO, bytes, str], 
               content_type: str=None,
               size: int=None, 
               metadata: Dict[str, Any]=None, 
               part_size:int = 100 * 1024 * 1024) -> ObjectMetadata:
    
    if isinstance(data, bytes):
        data_bytes_io = io.BytesIO(data)
        size = len(data)
    elif isinstance(data, str):
        encoded_data = data.encode('utf-8')
        data_bytes_io = io.BytesIO(encoded_data)
        size = len(encoded_data)
    else:
        data_bytes_io = data

    try:
        response = client.put_object(
            bucket, object, data_bytes_io, content_type=content_type,
            length=size, part_size=part_size, metadata=metadata)
        
        return ObjectMetadata.from_minio_write_response(response)

    except S3Error as se:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {se}")
        raise se
    except Exception as e:
        _LOGGER.error(f"Error putting object {object} in bucket {bucket}: {e}")
        raise e


def delete_object(client: Union[Minio, LocalFileStorage], bucket: str, object: str, version_id: Optional[str] = None):
    try:
        client.remove_object(bucket, object, version_id=version_id)
        
    except S3Error as se:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {se}")
        raise se
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise e


def create_bucket(client: Union[Minio, LocalFileStorage], workspace_name: str, excluded_prefixes: List[str]= EXCLUDED_VERSIONING_PREFIXES):
    try:
        client.make_bucket(workspace_name)
        try:
            client.set_bucket_versioning(workspace_name, VersioningConfig(ENABLED))
        except Exception as e:
            _LOGGER.error(f"Error enabling versioning for bucket {workspace_name}: {e}")

    except S3Error as se:
        if se.code in ['BucketAlreadyOwnedByYou', 'BucketAlreadyExists']:
            pass
        else:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {se}")
            raise se
    except Exception as e:
        _LOGGER.error(f"Error creating bucket {workspace_name}: {e}")
        raise e


def delete_bucket(client: Union[Minio, LocalFileStorage], workspace_name: str):
    if isinstance(client, LocalFileStorage):
        try:
            bucket_path = client._get_bucket_path(workspace_name)
            if bucket_path.exists() and bucket_path.is_dir():
                shutil.rmtree(bucket_path)
                _LOGGER.info(f"Locally deleted bucket directory: {bucket_path}")
        except Exception as e:
            _LOGGER.error(f"Error deleting local bucket directory {workspace_name}: {e}")
            raise e
    elif isinstance(client, Minio):
        try:
            # Existing Minio logic
            objects = client.list_objects(workspace_name, prefix="", recursive=True, include_version=True)
            # Convert generator to list to avoid issues during iteration
            obj_list = list(objects)
            for obj in obj_list:
                try:
                    client.remove_object(workspace_name, obj.object_name, version_id=obj.version_id)
                except S3Error as remove_err:
                    _LOGGER.warning(f"Error removing object {obj.object_name} (version: {obj.version_id}) during bucket delete: {remove_err}")

            client.remove_bucket(workspace_name)
        except S3Error as se:
            if se.code in {"NoSuchBucket", "NotImplemented"}:
                pass
            else:
                _LOGGER.error(f"Error deleting Minio bucket {workspace_name}: {se}")
                raise se
        except Exception as e:
            _LOGGER.error(f"Error deleting Minio bucket {workspace_name}: {e}")
            raise e
    else:
        _LOGGER.error(f"Unknown client type for delete_bucket: {type(client)}")
        raise TypeError("Unsupported client type for delete_bucket")


