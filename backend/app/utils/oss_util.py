# -*- coding: utf-8 -*-
import oss2
import logging
from typing import Tuple, Optional
from app.api.v1.module_system.params.service import ParamsService
from app.core.redis_crud import RedisCURD
from app.core.logger import logger

class OSSUtil:
    _bucket = None

    @classmethod
    async def get_bucket(cls, redis=None):
        """
        获取OSS Bucket对象
        需要先从系统配置中获取AK/SK/Endpoint/Bucket
        """
        # 如果没有redis，可能无法获取配置，这里假设调用方会传redis或者有其他方式获取配置
        # 但ParamsService.get_config_value_by_key_service需要AuthSchema? 
        # 实际上ParamsService.get_config_value_by_key_service需要auth参数，这有点麻烦。
        # 我们直接从Redis获取，或者假设已经有helper可以获取系统参数。
        # ParamsService.get_config_value_by_key_service calls ParamsCRUD which needs session.
        # 我们可以使用 ParamsService.get_system_config_for_middleware 的逻辑，直接从Redis读。
        
        # 为了简单起见，我们假设配置已经同步到Redis，或者我们每次都去查Redis。
        # 这是一个async方法。
        
        # 配置Key定义
        ACCESS_KEY_ID_KEY = "sys_oss_access_key_id"
        ACCESS_KEY_SECRET_KEY = "sys_oss_access_key_secret"
        ENDPOINT_KEY = "sys_oss_endpoint"
        BUCKET_NAME_KEY = "sys_oss_bucket_name"

        if not redis:
             raise Exception("Redis connection required to fetch OSS config")

        # 获取配置
        # ParamsService uses RedisInitKeyConfig.SYSTEM_CONFIG.key + ":" + config_key
        # We need to import RedisInitKeyConfig
        from app.common.enums import RedisInitKeyConfig
        
        prefix = RedisInitKeyConfig.SYSTEM_CONFIG.key
        keys = [
            f"{prefix}:{ACCESS_KEY_ID_KEY}",
            f"{prefix}:{ACCESS_KEY_SECRET_KEY}",
            f"{prefix}:{ENDPOINT_KEY}",
            f"{prefix}:{BUCKET_NAME_KEY}"
        ]
        
        values = await RedisCURD(redis).mget(keys)
        
        import json
        def get_val(v):
            if v:
                try:
                    obj = json.loads(v)
                    return obj.get("config_value")
                except:
                    return None
            return None

        access_key_id = get_val(values[0])
        access_key_secret = get_val(values[1])
        endpoint = get_val(values[2])
        bucket_name = get_val(values[3])

        if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
            logger.error("OSS configuration missing in system params")
            raise Exception("OSS configuration is incomplete. Please configure AccessKeyId, AccessKeySecret, Endpoint, and BucketName in system settings.")

        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        return bucket

    @classmethod
    async def upload_file(cls, redis, key: str, data: bytes) -> dict:
        """
        上传文件到OSS
        :param redis: Redis客户端
        :param key: OSS路径
        :param data: 文件内容
        :return: dict (etag, size, request_id)
        """
        try:
            bucket = await cls.get_bucket(redis)
            # put_object is blocking, should run in thread pool if file is large? 
            # oss2 is synchronous. We should wrap it.
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _put():
                return bucket.put_object(key, data)
            
            result = await loop.run_in_executor(None, _put)
            
            # Get object info to verify size/md5 if needed, but result contains etag/request_id
            # ETag in OSS is usually MD5 (uppercase).
            return {
                "etag": result.etag.replace('"', ''),
                "request_id": result.request_id
            }
        except Exception as e:
            logger.error(f"OSS Upload Failed: {e}")
            raise e

    @classmethod
    async def copy_file(cls, redis, source_key: str, target_key: str) -> dict:
        """
        在OSS内部复制文件
        """
        try:
            bucket = await cls.get_bucket(redis)
            import asyncio
            loop = asyncio.get_event_loop()

            def _copy():
                return bucket.copy_object(bucket.bucket_name, source_key, target_key)

            result = await loop.run_in_executor(None, _copy)
            return {
                "etag": result.etag.replace('"', ''),
                "request_id": result.request_id
            }
        except Exception as e:
            logger.error(f"OSS Copy Failed: {e}")
            raise e

    @classmethod
    async def get_object_meta(cls, redis, key: str) -> dict:
        """
        获取文件元数据 (Size, ETag/MD5)
        """
        try:
            bucket = await cls.get_bucket(redis)
            import asyncio
            loop = asyncio.get_event_loop()

            def _get_meta():
                return bucket.get_object_meta(key)

            result = await loop.run_in_executor(None, _get_meta)
            # result.content_length, result.etag, result.last_modified
            return {
                "size": result.content_length,
                "etag": result.etag.replace('"', ''), # OSS ETag is often MD5
                "last_modified": result.last_modified
            }
        except Exception as e:
            logger.error(f"OSS Get Meta Failed: {e}")
            raise e

    @classmethod
    async def delete_object(cls, redis, key: str):
        """
        删除文件
        """
        try:
            bucket = await cls.get_bucket(redis)
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _delete():
                bucket.delete_object(key)
                
            await loop.run_in_executor(None, _delete)
        except Exception as e:
            logger.error(f"OSS Delete Failed: {e}")
            raise e

