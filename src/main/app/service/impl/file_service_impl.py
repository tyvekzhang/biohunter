# SPDX-License-Identifier: MIT
"""File domain service impl"""

from __future__ import annotations

from datetime import datetime
import json
import os
import shutil
from typing import Optional
import uuid

import aiofiles
from fastapi import HTTPException, UploadFile

from fastlib.service.impl.base_service_impl import BaseServiceImpl
from fastlib.logging import logger
from fastlib.config.utils import ProjectInfo
from src.main.app.mapper.file_mapper import FileMapper
from src.main.app.model.file_model import FileModel
from src.main.app.schema.file_schema import (
    ChunkUploadResponse,
    ChunkedUploadStatus,
    InitChunkedUploadRequest,
    InitChunkedUploadResponse,
    MergeChunksResponse,
)
from src.main.app.service.file_service import FileService
from src.main.app.utils.file_util import calculate_chunk_sha256, calculate_file_sha256


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
        self.projec_name = ProjectInfo.from_pyproject().name.lower().replace(" ", "_")
        # Directory configuration
        self.UPLOAD_DIR = f"/data/{self.projec_name}/uploads"
        self.TEMP_DIR = f"/data/{self.projec_name}/temp_uploads"
        self.METADATA_DIR = f"/data/{self.projec_name}/metadata"
        
        # Create required directories
        for dir_path in [self.UPLOAD_DIR, self.TEMP_DIR, self.METADATA_DIR]:
            logger.info(f"Upload dir: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)

    async def check_file_exists_by_hash(self, file_hash: str) -> Optional[FileModel]:
        """Check if file exists by SHA-256 hash for instant upload"""
        # Query database for existing file with same hash
        existing_file = await self.mapper.find_by_hash(file_hash)
        if existing_file and existing_file.state == 1:
            return existing_file
        return None
    
    def get_metadata_path(self, upload_id: str) -> str:
        """Get metadata file path for upload session"""
        return os.path.join(self.METADATA_DIR, f"{upload_id}.json")
    
    def load_upload_metadata(self, upload_id: str) -> dict:
        """Load upload session metadata"""
        metadata_path = self.get_metadata_path(upload_id)
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=404, detail="Upload ID not found")
        
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def save_upload_metadata(self, upload_id: str, metadata: dict):
        """Save upload session metadata"""
        metadata_path = self.get_metadata_path(upload_id)
        metadata['updated_at'] = datetime.now().isoformat()
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def init_chunked_upload(
        self, req: InitChunkedUploadRequest
    ) -> InitChunkedUploadResponse:
        """
        Initialize chunked upload session.
        Returns instant upload response if file already exists.
        """
        # Check for instant upload possibility
        existing_file = await self.check_file_exists_by_hash(req.file_hash)
        if existing_file:
            return InitChunkedUploadResponse(
                status="instant",
                file_id=existing_file.id,
                message="File already exists, instant upload successful"
            )
        
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Create temporary upload directory
        temp_upload_dir = os.path.join(self.TEMP_DIR, upload_id)
        os.makedirs(temp_upload_dir, exist_ok=True)
        
        # Save upload metadata
        metadata = {
            "upload_id": upload_id,
            "original_name": req.original_name,
            "total_chunks": req.total_chunks,
            "uploaded_chunks": [],
            "file_size": req.file_size,
            "file_hash": req.file_hash,
            "file_extension": req.file_extension,
            "user_id": req.user_id,
            "conversation_id": req.conversation_id,
            "status": "uploading",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.save_upload_metadata(upload_id, metadata)
        
        # Create initial database record (state=0)
        file_model = FileModel(
            file_uuid=upload_id,
            storage_driver="local",
            storage_path=f"{self.TEMP_DIR}/{upload_id}",
            original_name=req.original_name,
            storage_name=f"{upload_id}_{req.original_name}",
            file_hash=req.file_hash,
            file_size=req.file_size,
            file_extension=req.file_extension,
            user_id=req.user_id,
            conversation_id=req.conversation_id,
            state=0  # Initial state
        )
        await self.mapper.insert(data=file_model)
        
        return InitChunkedUploadResponse(
            status="success",
            upload_id=upload_id,
            message="Upload initialized successfully"
        )
    
    async def upload_chunk(
        self, 
        upload_id: str,
        chunk_number: int,
        chunk_hash: str,
        file: UploadFile
    ) -> ChunkUploadResponse:
        """Upload a single chunk with SHA-256 validation"""
        try:
            # Load metadata
            metadata = self.load_upload_metadata(upload_id)
            
            # Check upload status
            if metadata['status'] not in ['uploading', 'paused']:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Upload is {metadata['status']}, cannot upload chunks"
                )
            
            # Validate chunk number
            if chunk_number < 0 or chunk_number >= metadata['total_chunks']:
                raise HTTPException(status_code=400, detail="Invalid chunk number")
            
            # Check if chunk already uploaded (for resumable uploads)
            if chunk_number in metadata['uploaded_chunks']:
                return ChunkUploadResponse(
                    chunk_number=chunk_number,
                    status="exists",
                    message="Chunk already uploaded"
                )
            
            # Read chunk content
            content = await file.read()
            
            # Verify chunk SHA-256
            actual_hash = calculate_chunk_sha256(content=content)
            if actual_hash != chunk_hash:
                raise HTTPException(
                    status_code=400,
                    detail=f"Chunk SHA-256 mismatch. Expected: {chunk_hash}, Got: {actual_hash}"
                )
            
            # Save chunk
            temp_upload_dir = os.path.join(self.TEMP_DIR, upload_id)
            chunk_path = os.path.join(temp_upload_dir, f"chunk_{chunk_number:06d}")
            
            async with aiofiles.open(chunk_path, 'wb') as f:
                await f.write(content)
            
            # Update metadata
            metadata['uploaded_chunks'].append(chunk_number)
            metadata['uploaded_chunks'].sort()
            self.save_upload_metadata(upload_id, metadata)
            
            return ChunkUploadResponse(
                chunk_number=chunk_number,
                status="success",
                message="Chunk uploaded successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def merge_chunks(self, upload_id: str) -> MergeChunksResponse:
        """Merge all chunks and verify final file integrity"""
        try:
            # Load metadata
            metadata = self.load_upload_metadata(upload_id)
            
            # Check if all chunks are uploaded
            if len(metadata['uploaded_chunks']) != metadata['total_chunks']:
                missing_chunks = set(range(metadata['total_chunks'])) - set(metadata['uploaded_chunks'])
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing chunks: {sorted(missing_chunks)}"
                )
            
            # Generate storage filename
            storage_name = f"{upload_id}_{metadata['original_name']}"
            final_path = os.path.join(self.UPLOAD_DIR, storage_name)
            
            # Merge chunks
            temp_upload_dir = os.path.join(self.TEMP_DIR, upload_id)
            with open(final_path, 'wb') as outfile:
                for chunk_number in range(metadata['total_chunks']):
                    chunk_path = os.path.join(temp_upload_dir, f"chunk_{chunk_number:06d}")
                    with open(chunk_path, 'rb') as infile:
                        outfile.write(infile.read())
            
            # Verify merged file SHA-256
            final_hash = calculate_file_sha256(final_path)
            if final_hash != metadata['file_hash']:
                os.remove(final_path)
                raise HTTPException(
                    status_code=500,
                    detail=f"File SHA-256 mismatch after merge"
                )
            
            # Update database record
            file_record = await self.mapper.find_by_uuid(upload_id)
            if file_record:
                file_record.storage_path = final_path
                file_record.state = 1  # Mark as completed
                await self.mapper.update(data=file_record)
            
            # Clean up temporary files
            shutil.rmtree(temp_upload_dir)
            
            # Update metadata status
            metadata['status'] = 'completed'
            metadata['final_path'] = final_path
            self.save_upload_metadata(upload_id, metadata)
            
            return MergeChunksResponse(
                status="success",
                file_id=file_record.id,
                file_uuid=upload_id,
                message="File merged successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_upload_status(self, upload_id: str) -> ChunkedUploadStatus:
        """Get detailed upload session status"""
        metadata = self.load_upload_metadata(upload_id)
        return ChunkedUploadStatus(
            upload_id=metadata['upload_id'],
            original_name=metadata['original_name'],
            total_chunks=metadata['total_chunks'],
            uploaded_chunks=metadata['uploaded_chunks'],
            file_size=metadata['file_size'],
            file_hash=metadata['file_hash'],
            status=metadata['status'],
            created_at=datetime.fromisoformat(metadata['created_at']),
            updated_at=datetime.fromisoformat(metadata['updated_at'])
        )
    
    async def pause_upload(self, upload_id: str) -> dict:
        """Pause an active upload session"""
        metadata = self.load_upload_metadata(upload_id)
        
        if metadata['status'] != 'uploading':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause upload with status: {metadata['status']}"
            )
        
        metadata['status'] = 'paused'
        self.save_upload_metadata(upload_id, metadata)
        
        return {
            "status": "success",
            "message": "Upload paused",
            "uploaded_chunks": metadata['uploaded_chunks']
        }
    
    async def resume_upload(self, upload_id: str) -> dict:
        """Resume a paused upload session"""
        metadata = self.load_upload_metadata(upload_id)
        
        if metadata['status'] != 'paused':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume upload with status: {metadata['status']}"
            )
        
        metadata['status'] = 'uploading'
        self.save_upload_metadata(upload_id, metadata)
        
        missing_chunks = set(range(metadata['total_chunks'])) - set(metadata['uploaded_chunks'])
        
        return {
            "status": "success",
            "message": "Upload resumed",
            "uploaded_chunks": metadata['uploaded_chunks'],
            "missing_chunks": sorted(missing_chunks)
        }
    
    async def cancel_upload(self, upload_id: str) -> dict:
        """Cancel upload session and clean up resources"""
        metadata = self.load_upload_metadata(upload_id)
        
        # Remove temporary files
        temp_upload_dir = os.path.join(self.TEMP_DIR, upload_id)
        if os.path.exists(temp_upload_dir):
            shutil.rmtree(temp_upload_dir)
        
        # Update metadata status
        metadata['status'] = 'cancelled'
        self.save_upload_metadata(upload_id, metadata)
        
        # Soft delete database record
        file_record = await self.mapper.find_by_uuid(upload_id)
        if file_record:
            file_record.deleted_at = datetime.now()
            await self.mapper.update(data=file_record)
        
        return {
            "status": "success",
            "message": "Upload cancelled and temporary files removed"
        }
    
    async def list_uploads(self, status: Optional[str] = None) -> list[ChunkedUploadStatus]:
        """list all upload sessions with optional status filter"""
        uploads = []
        
        for filename in os.listdir(self.METADATA_DIR):
            if filename.endswith('.json'):
                upload_id = filename[:-5]
                try:
                    metadata = self.load_upload_metadata(upload_id)
                    if status is None or metadata['status'] == status:
                        uploads.append(ChunkedUploadStatus(
                            upload_id=metadata['upload_id'],
                            original_name=metadata['original_name'],
                            total_chunks=metadata['total_chunks'],
                            uploaded_chunks=metadata['uploaded_chunks'],
                            file_size=metadata['file_size'],
                            file_hash=metadata['file_hash'],
                            status=metadata['status'],
                            created_at=datetime.fromisoformat(metadata['created_at']),
                            updated_at=datetime.fromisoformat(metadata['updated_at'])
                        ))
                except:
                    continue
        
        return uploads