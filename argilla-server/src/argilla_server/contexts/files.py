import io
import logging
import os
from typing import Any, BinaryIO, Dict, List, Optional, Union
from urllib.parse import urlparse
from uuid import UUID

from minio.commonconfig import ENABLED

from argilla_server.schemas.v1.files import ListObjectsResponse, ObjectMetadata, FileObjectResponse
from argilla_server.settings import settings
from fastapi import HTTPException
from minio import Minio, S3Error
from minio.helpers import ObjectWriteResult
from minio.versioningconfig import VersioningConfig
from minio.datatypes import Object

EXCLUDED_VERSIONING_PREFIXES = ['pdf']

_LOGGER = logging.getLogger("argilla")


def get_minio_client() -> Optional[Minio]:
    if None in [settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]:
        return None

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
        return None


def list_objects(client: Minio, bucket: str, prefix: Optional[str] = None, include_version=True) -> ListObjectsResponse:
    try:
        objects = client.list_objects(bucket, prefix=prefix, include_version=include_version)
        objects = [ObjectMetadata.from_minio_object(obj) for obj in objects]
        return ListObjectsResponse(objects=objects)
    
    except S3Error as se:
        _LOGGER.error(f"Error listing objects in '{bucket}/{prefix}': {se}")
        raise HTTPException(status_code=404, detail=f"Cannot list objects with '{bucket}/{prefix}' not found")
    except Exception as e:
        _LOGGER.error(f"Error listing objects in bucket '{bucket}/{prefix}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

def get_object(client: Minio, bucket: str, object: str, version_id: Optional[str] = None, 
               include_versions=False) -> FileObjectResponse:
    try:
        stat = client.stat_object(bucket, object, version_id=version_id)
    except S3Error as se:
        if version_id:
            _LOGGER.warn(f"Error getting object {object} from bucket {bucket} with version {version_id}: {se}")
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
        raise HTTPException(status_code=500, detail="Internal server error")
    

def put_object(client: Minio, bucket: str, object: str, data: Union[BinaryIO, bytes, str], 
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


def delete_object(client: Minio, bucket: str, object: str, version_id: Optional[str] = None):
    try:
        client.remove_object(bucket, object, version_id=version_id)
        
    except S3Error as se:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {se}")
        raise se
    except Exception as e:
        _LOGGER.error(f"Error deleting object {object} from bucket {bucket}: {e}")
        raise e


def create_bucket(client: Minio, workspace_name: str, excluded_prefixes: List[str]= EXCLUDED_VERSIONING_PREFIXES):
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


def delete_bucket(client: Minio, workspace_name: str):
    try:
        client.remove_bucket(workspace_name)
    except S3Error as se:
        if se.code == "NoSuchBucket":
            pass
        else:
            _LOGGER.error(f"Error creating bucket {workspace_name}: {se}")
            raise se
    except Exception as e:
        _LOGGER.error(f"Error deleting bucket {workspace_name}: {e}")
        raise e


def get_pdf_s3_object_path(id: Union[UUID, str]):
    if id is None:
        raise Exception("id cannot be None")
    elif isinstance(id, UUID):
        object_path = f'pdf/{str(id)}'
    else:
        object_path = f'pdf/{id}'

    return object_path


def get_s3_object_url(bucket_name:str, object_name:str)->str:
    return f'/api/v1/file/{bucket_name}/{object_name}'
