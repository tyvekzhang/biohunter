# SPDX-License-Identifier: MIT
"""Business exception for the application."""

from http import HTTPStatus
from typing import Any

from fastlib.exception import ErrorDetail
from fastlib.exception.base import BaseException


class BusinessErrorCode:
    """Business-related error codes."""

    USER_NAME_EXISTS = ErrorDetail(
        code=HTTPStatus.CONFLICT, message="Username already exists"
    )
    MENU_NAME_EXISTS = ErrorDetail(
        code=HTTPStatus.CONFLICT, message="Menu name already exists"
    )

    RESOURCE_NOT_FOUND = ErrorDetail(
        code=HTTPStatus.NOT_FOUND, message="Requested resource not found"
    )

    PARAMETER_ERROR = ErrorDetail(
        code=HTTPStatus.BAD_REQUEST, message="Parameter error"
    )


class BusinessException(BaseException):
    def __init__(
        self,
        code: BusinessErrorCode,
        message: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(code=code, message=message, details=details)
