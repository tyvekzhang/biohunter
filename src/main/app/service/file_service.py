# SPDX-License-Identifier: MIT
"""File Service"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type

from starlette.responses import StreamingResponse

from fastlib.service.base_service import BaseService
from src.main.app.model.file_model import FileModel
from src.main.app.schema.file_schema import (
    ListFilesRequest,
    CreateFileRequest,
    File,
    UpdateFileRequest,
    BatchDeleteFilesRequest,
    ExportFilesRequest,
    BatchCreateFilesRequest,
    BatchUpdateFilesRequest,
    ImportFilesRequest,
    ImportFile,
    BatchPatchFilesRequest,
)


class FileService(BaseService[FileModel], ABC):
    @abstractmethod
    async def get_file(
        self,
        *,
        id: int,
    ) -> FileModel: ...

    @abstractmethod
    async def list_files(
        self, *, req: ListFilesRequest
    ) -> tuple[list[FileModel], int]: ...

    

    @abstractmethod
    async def create_file(self, *, req: CreateFileRequest) -> FileModel: ...

    @abstractmethod
    async def update_file(self, req: UpdateFileRequest) -> FileModel: ...

    @abstractmethod
    async def delete_file(self, id: int) -> None: ...

    @abstractmethod
    async def batch_get_files(self, ids: list[int]) -> list[FileModel]: ...

    @abstractmethod
    async def batch_create_files(
        self,
        *,
        req: BatchCreateFilesRequest,
    ) -> list[FileModel]: ...

    @abstractmethod
    async def batch_update_files(
        self, req: BatchUpdateFilesRequest
    ) -> list[FileModel]: ...

    @abstractmethod
    async def batch_patch_files(
        self, req: BatchPatchFilesRequest
    ) -> list[FileModel]: ...

    @abstractmethod
    async def batch_delete_files(self, req: BatchDeleteFilesRequest): ...

    @abstractmethod
    async def export_files_template(self) -> StreamingResponse: ...

    @abstractmethod
    async def export_files(
        self, req: ExportFilesRequest
    ) -> StreamingResponse: ...

    @abstractmethod
    async def import_files(
        self, req: ImportFilesRequest
    ) -> list[ImportFile]: ...