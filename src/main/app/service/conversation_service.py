# SPDX-License-Identifier: MIT
"""Conversation Service"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type

from starlette.responses import StreamingResponse

from fastlib.service.base_service import BaseService
from src.main.app.model.conversation_model import ConversationModel
from src.main.app.schema.conversation_schema import (
    ListConversationsRequest,
    CreateConversationRequest,
    Conversation,
    UpdateConversationRequest,
    BatchDeleteConversationsRequest,
    ExportConversationsRequest,
    BatchCreateConversationsRequest,
    BatchUpdateConversationsRequest,
    ImportConversationsRequest,
    ImportConversation,
    BatchPatchConversationsRequest,
)


class ConversationService(BaseService[ConversationModel], ABC):
    @abstractmethod
    async def get_conversation(
        self,
        *,
        id: int,
    ) -> ConversationModel: ...

    @abstractmethod
    async def list_conversations(
        self, *, req: ListConversationsRequest
    ) -> tuple[list[ConversationModel], int]: ...

    

    @abstractmethod
    async def create_conversation(self, *, req: CreateConversationRequest) -> ConversationModel: ...

    @abstractmethod
    async def update_conversation(self, req: UpdateConversationRequest) -> ConversationModel: ...

    @abstractmethod
    async def delete_conversation(self, id: int) -> None: ...

    @abstractmethod
    async def batch_get_conversations(self, ids: list[int]) -> list[ConversationModel]: ...

    @abstractmethod
    async def batch_create_conversations(
        self,
        *,
        req: BatchCreateConversationsRequest,
    ) -> list[ConversationModel]: ...

    @abstractmethod
    async def batch_update_conversations(
        self, req: BatchUpdateConversationsRequest
    ) -> list[ConversationModel]: ...

    @abstractmethod
    async def batch_patch_conversations(
        self, req: BatchPatchConversationsRequest
    ) -> list[ConversationModel]: ...

    @abstractmethod
    async def batch_delete_conversations(self, req: BatchDeleteConversationsRequest): ...

    @abstractmethod
    async def export_conversations_template(self) -> StreamingResponse: ...

    @abstractmethod
    async def export_conversations(
        self, req: ExportConversationsRequest
    ) -> StreamingResponse: ...

    @abstractmethod
    async def import_conversations(
        self, req: ImportConversationsRequest
    ) -> list[ImportConversation]: ...