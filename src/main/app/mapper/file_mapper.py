# SPDX-License-Identifier: MIT
"""File mapper"""

from __future__ import annotations

from sqlmodel import select
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from fastlib.mapper.impl.base_mapper_impl import SqlModelMapper
from src.main.app.model.file_model import FileModel


class FileMapper(SqlModelMapper[FileModel]):
    async def find_by_hash(
        self, file_hash: str, db_session: Optional[AsyncSession] = None
    ) -> Optional[FileModel]:
        """Find file by SHA-256 hash"""

        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model)
            .where(self.model.file_hash == file_hash)
            .where(self.model.state == 1)
        )
        return result.one_or_none()

    async def find_by_uuid(
        self, file_uuid: str, db_session: Optional[AsyncSession] = None
    ) -> Optional[FileModel]:
        """Find file by UUID"""
        
        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model)
            .where(self.model.file_uuid == file_uuid)
            .where(self.model.deleted_at.is_not(None))
        )
        return result.one_or_none()

    async def find_by_user_and_conversation(
        self, 
        user_id: str, 
        conversation_id: str, 
        db_session: Optional[AsyncSession] = None
    ) -> list[FileModel]:
        """
        Retrieve files uploaded by the current user in a specific conversation.
        
        Args:
            user_id: The ID of the user
            conversation_id: The ID of the conversation
            db_session: Database session (optional)
                
        Returns:
            List[FileModel]: List of file models uploaded by the user in the conversation
        """
        db_session = db_session or self.db.session
        
        result = await db_session.exec(
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(self.model.conversation_id == conversation_id)
            .where(self.model.state == 1)
            .where(self.model.deleted_at.is_(None))
        )
        return result.all()

fileMapper = FileMapper(FileModel)
