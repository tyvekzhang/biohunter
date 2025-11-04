# SPDX-License-Identifier: MIT
"""Conversation mapper"""

from __future__ import annotations

from sqlmodel import select
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from fastlib.mapper.impl.base_mapper_impl import SqlModelMapper
from src.main.app.model.conversation_model import ConversationModel


class ConversationMapper(SqlModelMapper[ConversationModel]):
    pass


conversationMapper = ConversationMapper(ConversationModel)