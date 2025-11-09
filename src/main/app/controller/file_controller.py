# SPDX-License-Identifier: MIT
"""File REST Controller"""
from __future__ import annotations
from typing import Optional

from fastlib.contextvars import get_current_user
from fastapi import APIRouter, File, Query, Form, UploadFile

from src.main.app.mapper.file_mapper import fileMapper
from src.main.app.schema.file_schema import (
    ChunkUploadResponse,
    ChunkedUploadStatus,
    InitChunkedUploadRequest,
    InitChunkedUploadResponse,
    MergeChunksResponse,
)
from src.main.app.service.impl.file_service_impl import FileServiceImpl
from src.main.app.service.file_service import FileService

file_router = APIRouter()
file_service: FileService = FileServiceImpl(mapper=fileMapper)


@file_router.post("/files:initChunkedUpload")
async def init_chunked_upload(
    req: InitChunkedUploadRequest,
) -> InitChunkedUploadResponse:
    """
    Initialize chunked upload session with instant upload support.
    
    Args:
        req: Request containing file metadata and SHA-256 hash
        
    Returns:
        InitChunkedUploadResponse: Upload ID or instant upload confirmation
        
    Raises:
        HTTPException(403 Forbidden): If user lacks upload permission
    """
    req.user_id = get_current_user()
    return await file_service.init_chunked_upload(req)

@file_router.post("/files:uploadChunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    chunk_hash: str = Form(...),
    file: UploadFile = File(...)
) -> ChunkUploadResponse:
    """
    Upload a single file chunk with integrity verification.
    
    Args:
        upload_id: Upload session identifier
        chunk_number: Sequential chunk number
        chunk_hash: SHA-256 hash of chunk content
        file: Binary chunk content
        
    Returns:
        ChunkUploadResponse: Upload result for this chunk
        
    Raises:
        HTTPException(400 Bad Request): If chunk validation fails
        HTTPException(404 Not Found): If upload session doesn't exist
    """
    return await file_service.upload_chunk(
        upload_id=upload_id,
        chunk_number=chunk_number,
        chunk_hash=chunk_hash,
        file=file
    )

@file_router.get("/files:uploadStatus/{upload_id}")
async def get_upload_status(upload_id: str) -> ChunkedUploadStatus:
    """
    Get chunked upload status for resumable uploads.
    
    Args:
        upload_id: Upload session identifier
        
    Returns:
        ChunkedUploadStatus: Detailed upload progress information
        
    Raises:
        HTTPException(404 Not Found): If upload session doesn't exist
    """
    return await file_service.get_upload_status(upload_id)

@file_router.post("/files:mergeChunks/{upload_id}")
async def merge_chunks(upload_id: str) -> MergeChunksResponse:
    """
    Merge all uploaded chunks into final file.
    
    Args:
        upload_id: Upload session identifier
        
    Returns:
        MergeChunksResponse: Final file information including ID
        
    Raises:
        HTTPException(400 Bad Request): If chunks are incomplete
        HTTPException(500 Internal Server Error): If merge verification fails
    """
    return await file_service.merge_chunks(upload_id)

@file_router.post("/files:pauseUpload/{upload_id}")
async def pause_upload(upload_id: str) -> dict:
    """
    Pause an active chunked upload session.
    
    Args:
        upload_id: Upload session identifier
        
    Returns:
        dict: Pause confirmation with uploaded chunks list
        
    Raises:
        HTTPException(400 Bad Request): If upload cannot be paused
        HTTPException(404 Not Found): If upload session doesn't exist
    """
    return await file_service.pause_upload(upload_id)

@file_router.post("/files:resumeUpload/{upload_id}")
async def resume_upload(upload_id: str) -> dict:
    """
    Resume a paused chunked upload session.
    
    Args:
        upload_id: Upload session identifier
        
    Returns:
        dict: Resume confirmation with missing chunks list
        
    Raises:
        HTTPException(400 Bad Request): If upload cannot be resumed
        HTTPException(404 Not Found): If upload session doesn't exist
    """
    return await file_service.resume_upload(upload_id)

@file_router.delete("/files:cancelUpload/{upload_id}")
async def cancel_upload(upload_id: str) -> dict:
    """
    Cancel chunked upload and remove temporary files.
    
    Args:
        upload_id: Upload session identifier
        
    Returns:
        dict: Cancellation confirmation
        
    Raises:
        HTTPException(404 Not Found): If upload session doesn't exist
    """
    return await file_service.cancel_upload(upload_id)

@file_router.get("/files:listUploads")
async def list_uploads(
    status: Optional[str] = Query(None, description="Filter by upload status")
) -> list[ChunkedUploadStatus]:
    """
    List all chunked upload sessions.
    
    Args:
        status: Optional status filter (uploading, completed, paused, cancelled)
        
    Returns:
        List[ChunkedUploadStatus]: List of upload sessions
        
    Raises:
        HTTPException(403 Forbidden): If user lacks view permission
    """
    return await file_service.list_uploads(status=status)