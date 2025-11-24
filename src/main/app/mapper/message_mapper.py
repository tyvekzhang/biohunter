# SPDX-License-Identifier: MIT
"""Message mapper"""

from __future__ import annotations

from sqlmodel import select
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from fastlib.mapper.impl.base_mapper_impl import SqlModelMapper
from src.main.app.model.message_model import MessageModel


class MessageMapper(SqlModelMapper[MessageModel]):

    async def select_by_conversation_id, created_at(
        self, *, conversation_id, created_at: str, db_session: Optional[AsyncSession] = None
    ) -> Optional[MessageModel]:
        """
        Retrieve a record by conversation_id, created_at.
        """
        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model).where(self.model.conversation_id, created_at == conversation_id, created_at)
        )
        return result.one_or_none()

    async def select_by_conversation_id, created_at_list(
        self, *, conversation_id, created_at_list: list[str], db_session: Optional[AsyncSession] = None
    ) -> list[MessageModel]:
        """
        Retrieve records by list of conversation_id, created_at.
        """
        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model).where(self.model.conversation_id, created_at.in_(conversation_id, created_at_list))
        )
        return result.all()



messageMapper = MessageMapper(MessageModel)