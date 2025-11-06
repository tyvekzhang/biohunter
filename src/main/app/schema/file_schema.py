# SPDX-License-Identifier: MIT
"""File schema"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field

from fastlib.request import ListRequest


class ListFilesRequest(ListRequest):
    id: Optional[int] = None
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    create_at: Optional[datetime] = None


class File(BaseModel):
    id: int
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    create_at: Optional[datetime] = None
    conversation_id: Optional[int] = None


class FileDetail(BaseModel):
    id: int
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    create_at: Optional[datetime] = None
    conversation_id: Optional[int] = None


class CreateFile(BaseModel):
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    conversation_id: Optional[int] = None


class CreateFileRequest(BaseModel):
    file: CreateFile = Field(alias="file")


class UpdateFile(BaseModel):
    id: int
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    conversation_id: Optional[int] = None


class UpdateFileRequest(BaseModel):
    file: UpdateFile = Field(alias="file")


class BatchGetFilesResponse(BaseModel):
    files: list[FileDetail] = Field(default_factory=list, alias="files")


class BatchCreateFilesRequest(BaseModel):
    files: list[CreateFile] = Field(default_factory=list, alias="files")


class BatchCreateFilesResponse(BaseModel):
    files: list[File] = Field(default_factory=list, alias="files")


class BatchUpdateFile(BaseModel):
    file_name: Optional[str] = None
    format: Optional[str] = None
    file_size: Optional[int] = None
    conversation_id: Optional[int] = None


class BatchUpdateFilesRequest(BaseModel):
    ids: list[int]
    file: BatchUpdateFile = Field(alias="file")


class BatchPatchFilesRequest(BaseModel):
    files: list[UpdateFile] = Field(default_factory=list, alias="files")


class BatchUpdateFilesResponse(BaseModel):
     files: list[File] = Field(default_factory=list, alias="files")


class BatchDeleteFilesRequest(BaseModel):
    ids: list[int]


class ExportFile(File):
    pass


class ExportFilesRequest(BaseModel):
    ids: list[int]


class ImportFilesRequest(BaseModel):
    file: UploadFile


class ImportFile(CreateFile):
    err_msg: Optional[str] = Field(None, alias="errMsg")


class ImportFilesResponse(BaseModel):
    files: list[ImportFile] = Field(default_factory=list, alias="files")