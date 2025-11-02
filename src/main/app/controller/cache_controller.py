# SPDX-License-Identifier: MIT
"""Cache management API controllers"""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastlib.cache.manager import get_cache_client
from fastlib.response import HttpResponse

cache_router = APIRouter(prefix="/cache")

# ========== 基础键值对操作 ==========


@cache_router.post("/{key}")
async def set_value(
    key: str, value: Any, ex: int | None = None, nx: bool = False, xx: bool = False
) -> HttpResponse[bool]:
    """
    Set a value in cache.
    """
    try:
        cache = await get_cache_client()
        result = await cache.set(key, value)
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
