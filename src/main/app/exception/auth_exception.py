# SPDX-License-Identifier: MIT
"""Auth exception for the application."""

from http import HTTPStatus
from typing import Any

from fastlib.exception import ErrorDetail
from fastlib.exception.base import BaseException


class AuthErrorCode:
    """Authentication and authorization error codes."""

    AUTH_FAILED = ErrorDetail(
        code=HTTPStatus.UNAUTHORIZED, message="Username or password error"
    )
    TOKEN_EXPIRED = ErrorDetail(
        code=HTTPStatus.UNAUTHORIZED, message="Token has expired"
    )
    OPENAPI_FORBIDDEN = ErrorDetail(
        code=HTTPStatus.FORBIDDEN, message="OpenAPI is not ready"
    )
    MISSING_TOKEN = ErrorDetail(
        code=HTTPStatus.UNAUTHORIZED, message="Authentication token is missing"
    )


class AuthException(BaseException):
    code: AuthErrorCode
    message: str | None = None
    details: Any | None = None
