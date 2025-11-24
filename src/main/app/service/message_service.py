# SPDX-License-Identifier: MIT
"""Message Service"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type

from starlette.responses import StreamingResponse

from fastlib.service.base_service import BaseService
from src.main.app.model.message_model import MessageModel
from src.main.app.schema.message_schema import (
    ListMessagesRequest,
    CreateMessageRequest,
    Message,
    UpdateMessageRequest,
    BatchDeleteMessagesRequest,
    ExportMessagesRequest,
    BatchCreateMessagesRequest,
    BatchUpdateMessagesRequest,
    ImportMessagesRequest,
    ImportMessage,
    BatchPatchMessagesRequest,
)


class MessageService(BaseService[MessageModel], ABC):
    @abstractmethod
    async def get_message(
        self,
        *,
        id: int,
    ) -> MessageModel: ...

    @abstractmethod
    async def list_messages(
        self, *, req: ListMessagesRequest
    ) -> tuple[list[MessageModel], int]: ...

    

    @abstractmethod
    async def create_message(self, *, req: CreateMessageRequest) -> MessageModel: ...

    @abstractmethod
    async def update_message(self, req: UpdateMessageRequest) -> MessageModel: ...

    @abstractmethod
    async def delete_message(self, id: int) -> None: ...

    @abstractmethod
    async def batch_get_messages(self, ids: list[int]) -> list[MessageModel]: ...

    @abstractmethod
    async def batch_create_messages(
        self,
        *,
        req: BatchCreateMessagesRequest,
    ) -> list[MessageModel]: ...

    @abstractmethod
    async def batch_update_messages(
        self, req: BatchUpdateMessagesRequest
    ) -> list[MessageModel]: ...

    @abstractmethod
    async def batch_patch_messages(
        self, req: BatchPatchMessagesRequest
    ) -> list[MessageModel]: ...

    @abstractmethod
    async def batch_delete_messages(self, req: BatchDeleteMessagesRequest): ...

    @abstractmethod
    async def export_messages_template(self) -> StreamingResponse: ...

    @abstractmethod
    async def export_messages(
        self, req: ExportMessagesRequest
    ) -> StreamingResponse: ...

    @abstractmethod
    async def import_messages(
        self, req: ImportMessagesRequest
    ) -> list[ImportMessage]: ...