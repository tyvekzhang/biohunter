# SPDX-License-Identifier: MIT
"""File schema"""

from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Chunked upload related schemas
class InitChunkedUploadRequest(BaseModel):
    """Request for initializing chunked upload"""
    original_name: str
    total_chunks: int
    file_size: int
    file_hash: str  # SHA-256 hash
    file_extension: Optional[str] = None
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None

class InitChunkedUploadResponse(BaseModel):
    """Response for chunked upload initialization"""
    status: str
    upload_id: Optional[str] = None
    message: str

class ChunkUploadRequest(BaseModel):
    """Request for uploading a chunk"""
    upload_id: str
    chunk_number: int
    chunk_hash: str  # SHA-256

class ChunkUploadResponse(BaseModel):
    """Response for chunk upload"""
    chunk_number: int
    status: str
    message: str

class ChunkedUploadStatus(BaseModel):
    """Chunked upload status"""
    upload_id: str
    original_name: str
    total_chunks: int
    uploaded_chunks: List[int]
    file_size: int
    file_hash: str
    status: str  # 'uploading', 'completed', 'paused', 'cancelled'
    created_at: datetime
    updated_at: datetime

class MergeChunksResponse(BaseModel):
    """Response for chunk merging"""
    status: str
    file_id: int
    file_uuid: str
    message: str