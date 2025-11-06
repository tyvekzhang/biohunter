# SPDX-License-Identifier: MIT
"""File mapper"""

from __future__ import annotations

from sqlmodel import select
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from fastlib.mapper.impl.base_mapper_impl import SqlModelMapper
from src.main.app.model.file_model import FileModel


class FileMapper(SqlModelMapper[FileModel]):
    pass


fileMapper = FileMapper(FileModel)