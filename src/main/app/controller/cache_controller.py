# SPDX-License-Identifier: MIT
"""Cache management API controllers"""

from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastlib.response import HttpResponse
from fastlib.cache.manager import get_cache_client

cache_router = APIRouter(prefix="/cache")

# ========== 基础键值对操作 ==========

@cache_router.post("/{key}")
async def set_value(
    key: str,
    value: Any,
    ex: Optional[int] = None,
    nx: bool = False,
    xx: bool = False
) -> HttpResponse[bool]:
    """
    Set a value in cache.
    """
    try:
        cache = await get_cache_client()
        result = await cache.set(key, value, ex=ex, nx=nx, xx=xx)
        return HttpResponse.success(data=result, message="Value set successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set value: {str(e)}")

@cache_router.get("/{key}")
async def get_value(key: str) -> HttpResponse[Any]:
    """
    Get a value from cache.
    """
    try:
        cache = await get_cache_client()
        value = await cache.get(key)
        return HttpResponse.success(data=value, message="Value retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get value: {str(e)}")

@cache_router.delete("/keys/{key}")
async def delete_keys(key: str) -> HttpResponse[int]:
    """
    Delete one or more keys from cache.
    """
    try:
        cache = await get_cache_client()
        keys_list = [k.strip() for k in key.split(",")]
        count = await cache.delete(*keys_list)
        return HttpResponse.success(data=count, message=f"Deleted {count} keys")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete keys: {str(e)}")

@cache_router.get("/keys/{key}/exists")
async def keys_exist(key: str) -> HttpResponse[int]:
    """
    Check if one or more keys exist.
    """
    try:
        cache = await get_cache_client()
        keys_list = [k.strip() for k in key.split(",")]
        count = await cache.exists(*keys_list)
        return HttpResponse.success(data=count, message=f"{count} keys exist")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check key existence: {str(e)}")

@cache_router.post("/{key}/expire")
async def set_expire(key: str, seconds: int) -> HttpResponse[bool]:
    """
    Set expiration time for a key.
    """
    try:
        cache = await get_cache_client()
        result = await cache.expire(key, seconds)
        return HttpResponse.success(data=result, message="Expiration set successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set expiration: {str(e)}")

@cache_router.get("/{key}/ttl")
async def get_ttl(key: str) -> HttpResponse[int]:
    """
    Get time to live for a key.
    """
    try:
        cache = await get_cache_client()
        ttl = await cache.ttl(key)
        return HttpResponse.success(data=ttl, message="TTL retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get TTL: {str(e)}")

@cache_router.post("/{key}/increment")
async def increment_value(key: str, amount: int = 1) -> HttpResponse[int]:
    """
    Increment a numeric value.
    """
    try:
        cache = await get_cache_client()
        result = await cache.incr(key, amount)
        return HttpResponse.success(data=result, message="Value incremented successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to increment value: {str(e)}")

@cache_router.post("/{key}/decrement")
async def decrement_value(key: str, amount: int = 1) -> HttpResponse[int]:
    """
    Decrement a numeric value.
    """
    try:
        cache = await get_cache_client()
        result = await cache.decr(key, amount)
        return HttpResponse.success(data=result, message="Value decremented successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decrement value: {str(e)}")

# ========== 哈希表操作 ==========

@cache_router.post("/hash/{name}/{field}")
async def hash_set(name: str, field: str, value: Any) -> HttpResponse[int]:
    """
    Set hash field value.
    """
    try:
        cache = await get_cache_client()
        result = await cache.hset(name, field, value)
        return HttpResponse.success(data=result, message="Hash field set successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set hash field: {str(e)}")

@cache_router.get("/hash/{name}/{field}")
async def hash_get(name: str, field: str) -> HttpResponse[Any]:
    """
    Get hash field value.
    """
    try:
        cache = await get_cache_client()
        value = await cache.hget(name, field)
        return HttpResponse.success(data=value, message="Hash field retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hash field: {str(e)}")

@cache_router.get("/hash/{name}")
async def hash_get_all(name: str) -> HttpResponse[dict]:
    """
    Get all hash fields and values.
    """
    try:
        cache = await get_cache_client()
        result = await cache.hgetall(name)
        return HttpResponse.success(data=result, message="Hash retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hash: {str(e)}")

@cache_router.delete("/hash/{name}/{fields}")
async def hash_delete(name: str, fields: str) -> HttpResponse[int]:
    """
    Delete hash fields.
    """
    try:
        cache = await get_cache_client()
        fields_list = [f.strip() for f in fields.split(",")]
        result = await cache.hdel(name, *fields_list)
        return HttpResponse.success(data=result, message=f"Deleted {result} hash fields")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete hash fields: {str(e)}")

# ========== 列表操作 ==========

@cache_router.post("/list/{name}/left")
async def list_push_left(name: str, values: List[Any]) -> HttpResponse[int]:
    """
    Push values to the left of a list.
    """
    try:
        cache = await get_cache_client()
        result = await cache.lpush(name, *values)
        return HttpResponse.success(data=result, message="Values pushed to left successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to push values to left: {str(e)}")

@cache_router.post("/list/{name}/right")
async def list_push_right(name: str, values: List[Any]) -> HttpResponse[int]:
    """
    Push values to the right of a list.
    """
    try:
        cache = await get_cache_client()
        result = await cache.rpush(name, *values)
        return HttpResponse.success(data=result, message="Values pushed to right successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to push values to right: {str(e)}")

@cache_router.delete("/list/{name}/left")
async def list_pop_left(name: str) -> HttpResponse[Any]:
    """
    Pop value from the left of a list.
    """
    try:
        cache = await get_cache_client()
        result = await cache.lpop(name)
        return HttpResponse.success(data=result, message="Value popped from left successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pop value from left: {str(e)}")

@cache_router.delete("/list/{name}/right")
async def list_pop_right(name: str) -> HttpResponse[Any]:
    """
    Pop value from the right of a list.
    """
    try:
        cache = await get_cache_client()
        result = await cache.rpop(name)
        return HttpResponse.success(data=result, message="Value popped from right successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pop value from right: {str(e)}")

@cache_router.get("/list/{name}")
async def list_get_range(name: str, start: int = 0, end: int = -1) -> HttpResponse[List[Any]]:
    """
    Get a range of values from a list.
    """
    try:
        cache = await get_cache_client()
        result = await cache.lrange(name, start, end)
        return HttpResponse.success(data=result, message="List range retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get list range: {str(e)}")

# ========== 集合操作 ==========

@cache_router.post("/set/{name}")
async def set_add(name: str, values: List[Any]) -> HttpResponse[int]:
    """
    Add values to a set.
    """
    try:
        cache = await get_cache_client()
        result = await cache.sadd(name, *values)
        return HttpResponse.success(data=result, message="Values added to set successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add values to set: {str(e)}")

@cache_router.get("/set/{name}")
async def set_get_members(name: str) -> HttpResponse[List[Any]]:
    """
    Get all members of a set.
    """
    try:
        cache = await get_cache_client()
        result = await cache.smembers(name)
        return HttpResponse.success(data=result, message="Set members retrieved successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get set members: {str(e)}")

@cache_router.delete("/set/{name}/{values}")
async def set_remove(name: str, values: str) -> HttpResponse[int]:
    """
    Remove values from a set.
    """
    try:
        cache = await get_cache_client()
        values_list = [v.strip() for v in values.split(",")]
        result = await cache.srem(name, *values_list)
        return HttpResponse.success(data=result, message=f"Removed {result} values from set")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove values from set: {str(e)}")

# ========== 分布式锁操作 ==========

@cache_router.post("/lock/{lock_name}/acquire")
async def acquire_lock(
    lock_name: str,
    timeout: int = 10,
    blocking_timeout: int = 5
) -> HttpResponse[bool]:
    """
    Acquire a distributed lock.
    """
    try:
        cache = await get_cache_client()
        result = await cache.acquire_lock(lock_name, timeout, blocking_timeout)
        return HttpResponse.success(data=result, message="Lock acquired successfully" if result else "Failed to acquire lock")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acquire lock: {str(e)}")

@cache_router.post("/lock/{lock_name}/release")
async def release_lock(lock_name: str) -> HttpResponse[bool]:
    """
    Release a distributed lock.
    """
    try:
        cache = await get_cache_client()
        result = await cache.release_lock(lock_name)
        return HttpResponse.success(data=result, message="Lock released successfully" if result else "Failed to release lock")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to release lock: {str(e)}")

# ========== 系统管理操作 ==========

@cache_router.get("/health/ping")
async def cache_ping() -> HttpResponse[bool]:
    """
    Check cache health.
    """
    try:
        cache = await get_cache_client()
        result = await cache.ping()
        return HttpResponse.success(data=result, message="Cache is healthy")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache health check failed: {str(e)}")

@cache_router.post("/clear")
async def clear_cache() -> HttpResponse[None]:
    """
    Clear all cached data.
    """
    try:
        cache = await get_cache_client()
        cache.clear()
        return HttpResponse.success(message="Cache cleared successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@cache_router.post("/close")
async def close_cache() -> HttpResponse[None]:
    """
    Close cache connection and clean up resources.
    """
    try:
        cache = await get_cache_client()
        await cache.close()
        return HttpResponse.success(message="Cache closed successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close cache: {str(e)}")