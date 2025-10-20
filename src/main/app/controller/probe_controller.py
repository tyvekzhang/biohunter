# SPDX-License-Identifier: MIT
"""Project health probe"""

from fastapi import APIRouter
from fastlib.response import HttpResponse

probe_router = APIRouter()


@probe_router.get("/probes:liveness")
async def liveness() -> HttpResponse[str]:
    """
    Check if the system is alive.

    Returns:
        HttpResponse[str]: An HTTP response containing a success message
        with the string "Hi".
    """
    return HttpResponse.success(message="Hi")
