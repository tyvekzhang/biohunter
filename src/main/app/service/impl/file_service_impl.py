# SPDX-License-Identifier: MIT
"""File domain service impl"""

from __future__ import annotations

import io
import json
from typing import Type, Any

import pandas as pd
from loguru import logger
from pydantic import ValidationError
from starlette.responses import StreamingResponse

from fastlib.constants import FilterOperators
from fastlib.service.impl.base_service_impl import BaseServiceImpl
from fastlib.utils import excel_util
from fastlib.utils.validate_util import ValidateService
from src.main.app.exception.biz_exception import BusinessErrorCode
from src.main.app.exception.biz_exception import BusinessException
from src.main.app.mapper.file_mapper import FileMapper
from src.main.app.model.file_model import FileModel
from src.main.app.schema.file_schema import (
    ListFilesRequest,
    File,
    CreateFileRequest,
    UpdateFileRequest,
    BatchDeleteFilesRequest,
    ExportFilesRequest,
    BatchCreateFilesRequest,
    CreateFile,
    BatchUpdateFilesRequest,
    UpdateFile,
    ImportFilesRequest,
    ImportFile,
    ExportFile,
    BatchPatchFilesRequest,
    BatchUpdateFile,
)
from src.main.app.service.file_service import FileService


class FileServiceImpl(BaseServiceImpl[FileMapper, FileModel], FileService):
    """
    Implementation of the FileService interface.
    """

    def __init__(self, mapper: FileMapper):
        """
        Initialize the FileServiceImpl instance.

        Args:
            mapper (FileMapper): The FileMapper instance to use for database operations.
        """
        super().__init__(mapper=mapper, model=FileModel)
        self.mapper = mapper

    async def get_file(
        self,
        *,
        id: int,
    ) -> FileModel:
        file_record: FileModel = await self.mapper.select_by_id(id=id)
        if file_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        return file_record

    async def list_files(
        self, req: ListFilesRequest
    ) -> tuple[list[FileModel], int]:
        filters = {
            FilterOperators.EQ: {},
            FilterOperators.NE: {},
            FilterOperators.GT: {},
            FilterOperators.GE: {},
            FilterOperators.LT: {},
            FilterOperators.LE: {},
            FilterOperators.BETWEEN: {},
            FilterOperators.LIKE: {},
        }
        if req.id is not None and req.id != "":
            filters[FilterOperators.EQ]["id"] = req.id
        if req.file_name is not None and req.file_name != "":
            filters[FilterOperators.LIKE]["file_name"] = req.file_name
        if req.format is not None and req.format != "":
            filters[FilterOperators.EQ]["format"] = req.format
        if req.file_size is not None and req.file_size != "":
            filters[FilterOperators.EQ]["file_size"] = req.file_size
        if req.created_at is not None and req.created_at != "":
            filters[FilterOperators.EQ]["created_at"] = req.created_at
        sort_list = None
        sort_str = req.sort_str
        if sort_str is not None:
            sort_list = json.loads(sort_str)
        return await self.mapper.select_by_ordered_page(
            current=req.current,
            page_size=req.page_size,
            count=req.count,
            **filters,
            sort_list=sort_list,
        )

    

    async def create_file(self, req: CreateFileRequest) -> FileModel:
        file: FileModel = FileModel(**req.file.model_dump())
        return await self.save(data=file)

    async def update_file(self, req: UpdateFileRequest) -> FileModel:
        file_record: FileModel = await self.retrieve_by_id(id=req.file.id)
        if file_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        file_model = FileModel(**req.file.model_dump(exclude_unset=True))
        await self.modify_by_id(data=file_model)
        merged_data = {**file_record.model_dump(), **file_model.model_dump()}
        return FileModel(**merged_data)

    async def delete_file(self, id: int) -> None:
        file_record: FileModel = await self.retrieve_by_id(id=id)
        if file_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        await self.mapper.delete_by_id(id=id)

    async def batch_get_files(self, ids: list[int]) -> list[FileModel]:
        file_records = list[FileModel] = await self.retrieve_by_ids(ids=ids)
        if file_records is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        if len(file_records) != len(ids):
            not_exits_ids = [id for id in ids if id not in file_records]
            raise BusinessException(
                BusinessErrorCode.RESOURCE_NOT_FOUND,
                f"{BusinessErrorCode.RESOURCE_NOT_FOUND.message}: {str(file_records)} != {str(not_exits_ids)}",
            )
        return file_records

    async def batch_create_files(
        self,
        *,
        req: BatchCreateFilesRequest,
    ) -> list[FileModel]:
        file_list: list[CreateFile] = req.files
        if not file_list:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        data_list = [FileModel(**file.model_dump()) for file in file_list]
        await self.mapper.batch_insert(data_list=data_list)
        return data_list

    async def batch_update_files(
        self, req: BatchUpdateFilesRequest
    ) -> list[FileModel]:
        file: BatchUpdateFile = req.file
        ids: list[int] = req.ids
        if not file or not ids:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        await self.mapper.batch_update_by_ids(
            ids=ids, data=file.model_dump(exclude_none=True)
        )
        return await self.mapper.select_by_ids(ids=ids)

    async def batch_patch_files(
        self, req: BatchPatchFilesRequest
    ) -> list[FileModel]:
        files: list[UpdateFile] = req.files
        if not files:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        update_data: list[dict[str, Any]] = [
            file.model_dump(exclude_unset=True) for file in files
        ]
        await self.mapper.batch_update(items=update_data)
        file_ids: list[int] = [file.id for file in files]
        return await self.mapper.select_by_ids(ids=file_ids)

    async def batch_delete_files(self, req: BatchDeleteFilesRequest):
        ids: list[int] = req.ids
        await self.mapper.batch_delete_by_ids(ids=ids)

    async def export_files_template(self) -> StreamingResponse:
        file_name = "file_import_tpl"
        return await excel_util.export_excel(
            schema=CreateFile, file_name=file_name
        )

    async def export_files(self, req: ExportFilesRequest) -> StreamingResponse:
        ids: list[int] = req.ids
        file_list: list[FileModel] = await self.mapper.select_by_ids(ids=ids)
        if file_list is None or len(file_list) == 0:
            logger.error(f"No files found with ids {ids}")
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        file_page_list = [ExportFile(**file.model_dump()) for file in file_list]
        file_name = "file_data_export"
        return await excel_util.export_excel(
            schema=ExportFile, file_name=file_name, data_list=file_page_list
        )

    async def import_files(self, req: ImportFilesRequest) -> list[ImportFile]:
        file = req.file
        contents = await file.read()
        import_df = pd.read_excel(io.BytesIO(contents))
        import_df = import_df.fillna("")
        file_records = import_df.to_dict(orient="records")
        if file_records is None or len(file_records) == 0:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        for record in file_records:
            for key, value in record.items():
                if value == "":
                    record[key] = None
        file_import_list = []
        for file_record in file_records:
            try:
                file_create = ImportFile(**file_record)
                file_import_list.append(file_create)
            except ValidationError as e:
                valid_data = {
                    k: v
                    for k, v in file_record.items()
                    if k in ImportFile.model_fields
                }
                file_create = ImportFile.model_construct(**valid_data)
                file_create.err_msg = ValidateService.get_validate_err_msg(e)
                file_import_list.append(file_create)
                return file_import_list

        return file_import_list