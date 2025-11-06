# SPDX-License-Identifier: MIT
"""File REST Controller"""
from __future__ import annotations
from typing import Annotated

from fastlib.response import ListResponse
from fastapi import APIRouter, Query, Form
from starlette.responses import StreamingResponse

from src.main.app.mapper.file_mapper import fileMapper
from src.main.app.model.file_model import FileModel
from src.main.app.schema.file_schema import (
    ListFilesRequest,
    File,
    CreateFileRequest,
    FileDetail,
    UpdateFileRequest,
    BatchDeleteFilesRequest,
    BatchUpdateFilesRequest,
    BatchUpdateFilesResponse,
    BatchCreateFilesRequest,
    BatchCreateFilesResponse,
    ExportFilesRequest,
    ImportFilesResponse,
    BatchGetFilesResponse,
    ImportFilesRequest,
    ImportFile, BatchPatchFilesRequest,
)
from src.main.app.service.impl.file_service_impl import FileServiceImpl
from src.main.app.service.file_service import FileService

file_router = APIRouter()
file_service: FileService = FileServiceImpl(mapper=fileMapper)


@file_router.get("/files/{id}")
async def get_file(id: int) -> FileDetail:
    """
    Retrieve file details.

    Args:

        id: Unique ID of the file resource.

    Returns:

        FileDetail: The file object containing all its details.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have permission.
        HTTPException(404 Not Found): If the requested file does not exist.
    """
    file_record: FileModel = await file_service.get_file(id=id)
    return FileDetail(**file_record.model_dump())


@file_router.get("/files")
async def list_files(
    req: Annotated[ListFilesRequest, Query()],
) -> ListResponse[File]:
    """
    List files with pagination.

    Args:

        req: Request object containing pagination, filter and sort parameters.

    Returns:

        ListResponse: Paginated list of files and total count.

    Raises:

        HTTPException(403 Forbidden): If user don't have access rights.
    """
    file_records, total = await file_service.list_files(req=req)
    return ListResponse(records=file_records, total=total)


@file_router.post("/files")
async def creat_file(
    req: CreateFileRequest,
) -> File:
    """
    Create a new file.

    Args:

        req: Request object containing file creation data.

    Returns:

         File: The file object.

    Raises:

        HTTPException(403 Forbidden): If the current user don't have access rights.
        HTTPException(409 Conflict): If the creation data already exists.
    """
    file: FileModel = await file_service.create_file(req=req)
    return File(**file.model_dump())


@file_router.put("/files")
async def update_file(
    req: UpdateFileRequest,
) -> File:
    """
    Update an existing file.

    Args:

        req: Request object containing file update data.

    Returns:

        File: The updated file object.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have update permissions.
        HTTPException(404 Not Found): If the file to update doesn't exist.
    """
    file: FileModel = await file_service.update_file(req=req)
    return File(**file.model_dump())


@file_router.delete("/files/{id}")
async def delete_file(
    id: int,
) -> None:
    """
    Delete file by ID.

    Args:

        id: The ID of the file to delete.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have access permissions.
        HTTPException(404 Not Found): If the file with given ID doesn't exist.
    """
    await file_service.delete_file(id=id)


@file_router.get("/files:batchGet")
async def batch_get_files(
    ids: list[int] = Query(..., description="List of file IDs to retrieve"),
) -> BatchGetFilesResponse:
    """
    Retrieves multiple files by their IDs.

    Args:

        ids (list[int]): A list of file resource IDs.

    Returns:

        list[FileDetail]: A list of file objects matching the provided IDs.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have access rights.
        HTTPException(404 Not Found): If one of the requested files does not exist.
    """
    file_records: list[FileModel] = await file_service.batch_get_files(ids)
    file_detail_list: list[FileDetail] = [
        FileDetail(**file_record.model_dump()) for file_record in file_records
    ]
    return BatchGetFilesResponse(files=file_detail_list)


@file_router.post("/files:batchCreate")
async def batch_create_files(
    req: BatchCreateFilesRequest,
) -> BatchCreateFilesResponse:
    """
    Batch create files.

    Args:

        req (BatchCreateFilesRequest): Request body containing a list of file creation items.

    Returns:

        BatchCreateFilesResponse: Response containing the list of created files.

    Raises:

        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(409 Conflict): If any file creation data already exists.
    """

    file_records = await file_service.batch_create_files(req=req)
    file_list: list[File] = [
        File(**file_record.model_dump()) for file_record in file_records
    ]
    return BatchCreateFilesResponse(files=file_list)


@file_router.post("/files:batchUpdate")
async def batch_update_files(
    req: BatchUpdateFilesRequest,
) -> BatchUpdateFilesResponse:
    """
    Batch update multiple files with the same changes.

    Args:

        req (BatchUpdateFilesRequest): The batch update request data with ids.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated files.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify files
        HTTPException 404 (Not Found): If any specified file ID doesn't exist
    """
    file_records: list[FileModel] = await file_service.batch_update_files(req=req)
    file_list: list[File] = [File(**file.model_dump()) for file in file_records]
    return BatchUpdateFilesResponse(files=file_list)


@file_router.post("/files:batchPatch")
async def batch_patch_files(
    req: BatchPatchFilesRequest,
) -> BatchUpdateFilesResponse:
    """
    Batch update multiple files with individual changes.

    Args:

        req (BatchPatchFilesRequest): The batch patch request data.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated files.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify files
        HTTPException 404 (Not Found): If any specified file ID doesn't exist
    """
    file_records: list[FileModel] = await file_service.batch_patch_files(req=req)
    file_list: list[File] = [File(**file.model_dump()) for file in file_records]
    return BatchUpdateFilesResponse(files=file_list)


@file_router.post("/files:batchDelete")
async def batch_delete_files(
    req: BatchDeleteFilesRequest,
) -> None:
    """
    Batch delete files.

    Args:
        req (BatchDeleteFilesRequest): Request object containing delete info.

    Raises:
        HTTPException(404 Not Found): If any of the files do not exist.
        HTTPException(403 Forbidden): If user don't have access rights.
    """
    await file_service.batch_delete_files(req=req)


@file_router.get("/files:exportTemplate")
async def export_files_template() -> StreamingResponse:
    """
    Export the Excel template for file import.

    Returns:
        StreamingResponse: An Excel file stream containing the import template.

    Raises:
        HTTPException(403 Forbidden): If user don't have access rights.
    """

    return await file_service.export_files_template()


@file_router.get("/files:export")
async def export_files(
    req: ExportFilesRequest = Query(...),
) -> StreamingResponse:
    """
    Export file data based on the provided file IDs.

    Args:
        req (ExportFilesRequest): Query parameters specifying the files to export.

    Returns:
        StreamingResponse: A streaming response containing the generated Excel file.

    Raises:
        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(404 Not Found ): If no matching files are found.
    """
    return await file_service.export_files(
        req=req,
    )

@file_router.post("/files:import")
async def import_files(
    req: ImportFilesRequest = Form(...),
) -> ImportFilesResponse:
    """
    Import files from an uploaded Excel file.

    Args:
        req (UploadFile): The Excel file containing file data to import.

    Returns:
        ImportFilesResponse: List of successfully parsed file data.

    Raises:
        HTTPException(400 Bad Request): If the uploaded file is invalid or cannot be parsed.
        HTTPException(403 Forbidden): If the current user lacks access rights.
    """

    import_files_resp: list[ImportFile] = await file_service.import_files(
        req=req
    )
    return ImportFilesResponse(files=import_files_resp)