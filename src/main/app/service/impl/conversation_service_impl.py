# SPDX-License-Identifier: MIT
"""Conversation domain service impl"""

from __future__ import annotations

import io
import json
from typing import Any

import pandas as pd
from loguru import logger
from pydantic import ValidationError
from starlette.responses import StreamingResponse

from fastlib.constants import FilterOperators
from fastlib.service.impl.base_service_impl import BaseServiceImpl
from fastlib.utils import excel_util
from fastlib.utils.validate_util import ValidateService
from src.main.app.exception.biz_exception import BusinessErrorCode
from src.main.app.exception.biz_exception import BusinessException
from src.main.app.mapper.conversation_mapper import ConversationMapper
from src.main.app.model.conversation_model import ConversationModel
from src.main.app.schema.conversation_schema import (
    ListConversationsRequest,
    CreateConversationRequest,
    UpdateConversationRequest,
    BatchDeleteConversationsRequest,
    ExportConversationsRequest,
    BatchCreateConversationsRequest,
    CreateConversation,
    BatchUpdateConversationsRequest,
    UpdateConversation,
    ImportConversationsRequest,
    ImportConversation,
    ExportConversation,
    BatchPatchConversationsRequest,
    BatchUpdateConversation,
)
from src.main.app.service.conversation_service import ConversationService


class ConversationServiceImpl(BaseServiceImpl[ConversationMapper, ConversationModel], ConversationService):
    """
    Implementation of the ConversationService interface.
    """

    def __init__(self, mapper: ConversationMapper):
        """
        Initialize the ConversationServiceImpl instance.

        Args:
            mapper (ConversationMapper): The ConversationMapper instance to use for database operations.
        """
        super().__init__(mapper=mapper, model=ConversationModel)
        self.mapper = mapper

    async def get_conversation(
        self,
        *,
        id: int,
    ) -> ConversationModel:
        conversation_record: ConversationModel = await self.mapper.select_by_id(id=id)
        if conversation_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        return conversation_record

    async def list_conversations(
        self, req: ListConversationsRequest
    ) -> tuple[list[ConversationModel], int]:
        filters = {
            FilterOperators.EQ: {},
            FilterOperators.NE: {},
            FilterOperators.GT: {},
            FilterOperators.GE: {},
            FilterOperators.LT: {},
            FilterOperators.LE: {},
            FilterOperators.BETWEEN: {},
            FilterOperators.LIKE: {},
        }
        if req.id is not None and req.id != "":
            filters[FilterOperators.EQ]["id"] = req.id
        if req.title is not None and req.title != "":
            filters[FilterOperators.EQ]["title"] = req.title
        if req.created_at is not None and req.created_at != "":
            filters[FilterOperators.EQ]["created_at"] = req.created_at
        if req.update_at is not None and req.update_at != "":
            filters[FilterOperators.EQ]["update_at"] = req.update_at
        sort_list = None
        sort_str = req.sort_str
        if sort_str is not None:
            sort_list = json.loads(sort_str)
        return await self.mapper.select_by_ordered_page(
            current=req.current,
            page_size=req.page_size,
            count=req.count,
            **filters,
            sort_list=sort_list,
        )

    

    async def create_conversation(self, req: CreateConversationRequest) -> ConversationModel:
        conversation: ConversationModel = ConversationModel(**req.conversation.model_dump())
        return await self.save(data=conversation)

    async def update_conversation(self, req: UpdateConversationRequest) -> ConversationModel:
        conversation_record: ConversationModel = await self.retrieve_by_id(id=req.conversation.id)
        if conversation_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        conversation_model = ConversationModel(**req.conversation.model_dump(exclude_unset=True))
        await self.modify_by_id(data=conversation_model)
        merged_data = {**conversation_record.model_dump(), **conversation_model.model_dump()}
        return ConversationModel(**merged_data)

    async def delete_conversation(self, id: int) -> None:
        conversation_record: ConversationModel = await self.retrieve_by_id(id=id)
        if conversation_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        await self.mapper.delete_by_id(id=id)

    async def batch_get_conversations(self, ids: list[int]) -> list[ConversationModel]:
        conversation_records = list[ConversationModel] = await self.retrieve_by_ids(ids=ids)
        if conversation_records is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        if len(conversation_records) != len(ids):
            not_exits_ids = [id for id in ids if id not in conversation_records]
            raise BusinessException(
                BusinessErrorCode.RESOURCE_NOT_FOUND,
                f"{BusinessErrorCode.RESOURCE_NOT_FOUND.message}: {str(conversation_records)} != {str(not_exits_ids)}",
            )
        return conversation_records

    async def batch_create_conversations(
        self,
        *,
        req: BatchCreateConversationsRequest,
    ) -> list[ConversationModel]:
        conversation_list: list[CreateConversation] = req.conversations
        if not conversation_list:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        data_list = [ConversationModel(**conversation.model_dump()) for conversation in conversation_list]
        await self.mapper.batch_insert(data_list=data_list)
        return data_list

    async def batch_update_conversations(
        self, req: BatchUpdateConversationsRequest
    ) -> list[ConversationModel]:
        conversation: BatchUpdateConversation = req.conversation
        ids: list[int] = req.ids
        if not conversation or not ids:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        await self.mapper.batch_update_by_ids(
            ids=ids, data=conversation.model_dump(exclude_none=True)
        )
        return await self.mapper.select_by_ids(ids=ids)

    async def batch_patch_conversations(
        self, req: BatchPatchConversationsRequest
    ) -> list[ConversationModel]:
        conversations: list[UpdateConversation] = req.conversations
        if not conversations:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        update_data: list[dict[str, Any]] = [
            conversation.model_dump(exclude_unset=True) for conversation in conversations
        ]
        await self.mapper.batch_update(items=update_data)
        conversation_ids: list[int] = [conversation.id for conversation in conversations]
        return await self.mapper.select_by_ids(ids=conversation_ids)

    async def batch_delete_conversations(self, req: BatchDeleteConversationsRequest):
        ids: list[int] = req.ids
        await self.mapper.batch_delete_by_ids(ids=ids)

    async def export_conversations_template(self) -> StreamingResponse:
        file_name = "conversation_import_tpl"
        return await excel_util.export_excel(
            schema=CreateConversation, file_name=file_name
        )

    async def export_conversations(self, req: ExportConversationsRequest) -> StreamingResponse:
        ids: list[int] = req.ids
        conversation_list: list[ConversationModel] = await self.mapper.select_by_ids(ids=ids)
        if conversation_list is None or len(conversation_list) == 0:
            logger.error(f"No conversations found with ids {ids}")
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        conversation_page_list = [ExportConversation(**conversation.model_dump()) for conversation in conversation_list]
        file_name = "conversation_data_export"
        return await excel_util.export_excel(
            schema=ExportConversation, file_name=file_name, data_list=conversation_page_list
        )

    async def import_conversations(self, req: ImportConversationsRequest) -> list[ImportConversation]:
        file = req.file
        contents = await file.read()
        import_df = pd.read_excel(io.BytesIO(contents))
        import_df = import_df.fillna("")
        conversation_records = import_df.to_dict(orient="records")
        if conversation_records is None or len(conversation_records) == 0:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        for record in conversation_records:
            for key, value in record.items():
                if value == "":
                    record[key] = None
        conversation_import_list = []
        for conversation_record in conversation_records:
            try:
                conversation_create = ImportConversation(**conversation_record)
                conversation_import_list.append(conversation_create)
            except ValidationError as e:
                valid_data = {
                    k: v
                    for k, v in conversation_record.items()
                    if k in ImportConversation.model_fields
                }
                conversation_create = ImportConversation.model_construct(**valid_data)
                conversation_create.err_msg = ValidateService.get_validate_err_msg(e)
                conversation_import_list.append(conversation_create)
                return conversation_import_list

        return conversation_import_list