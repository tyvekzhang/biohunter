# SPDX-License-Identifier: MIT
"""File Service"""

from __future__ import annotations
from abc import ABC, abstractmethod


from fastapi import UploadFile
from fastlib.service.base_service import BaseService
from src.main.app.model.file_model import FileModel
from src.main.app.schema.file_schema import (
    ChunkUploadResponse,
    ChunkedUploadStatus,
    InitChunkedUploadRequest,
    InitChunkedUploadResponse,
    MergeChunksResponse,
)


class FileService(BaseService[FileModel], ABC):
    @abstractmethod
    async def init_chunked_upload(
        self, req: InitChunkedUploadRequest
    ) -> InitChunkedUploadResponse:
        """Initialize chunked upload session"""
        pass
    
    @abstractmethod
    async def upload_chunk(
        self, 
        upload_id: str,
        chunk_number: int,
        chunk_hash: str,
        file: UploadFile
    ) -> ChunkUploadResponse:
        """Upload a single chunk"""
        pass
    
    @abstractmethod
    async def get_upload_status(
        self, upload_id: str
    ) -> ChunkedUploadStatus:
        """Get upload session status"""
        pass
    
    @abstractmethod
    async def merge_chunks(
        self, upload_id: str
    ) -> MergeChunksResponse:
        """Merge all chunks into final file"""
        pass
    
    @abstractmethod
    async def pause_upload(self, upload_id: str) -> dict:
        """Pause upload session"""
        pass
    
    @abstractmethod
    async def resume_upload(self, upload_id: str) -> dict:
        """Resume paused upload session"""
        pass
    
    @abstractmethod
    async def cancel_upload(self, upload_id: str) -> dict:
        """Cancel upload session and cleanup"""
        pass