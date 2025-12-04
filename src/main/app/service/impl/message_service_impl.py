# SPDX-License-Identifier: MIT
"""Message domain service impl"""

from __future__ import annotations

import io
import json
from typing import Type, Any

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
from src.main.app.mapper.message_mapper import MessageMapper
from src.main.app.model.message_model import MessageModel
from src.main.app.schema.message_schema import (
    ListMessagesRequest,
    Message,
    CreateMessageRequest,
    UpdateMessageRequest,
    BatchDeleteMessagesRequest,
    ExportMessagesRequest,
    BatchCreateMessagesRequest,
    CreateMessage,
    BatchUpdateMessagesRequest,
    UpdateMessage,
    ImportMessagesRequest,
    ImportMessage,
    ExportMessage,
    BatchPatchMessagesRequest,
    BatchUpdateMessage,
)
from src.main.app.service.message_service import MessageService


class MessageServiceImpl(BaseServiceImpl[MessageMapper, MessageModel], MessageService):
    """
    Implementation of the MessageService interface.
    """

    def __init__(self, mapper: MessageMapper):
        """
        Initialize the MessageServiceImpl instance.

        Args:
            mapper (MessageMapper): The MessageMapper instance to use for database operations.
        """
        super().__init__(mapper=mapper, model=MessageModel)
        self.mapper = mapper

    async def get_message(
        self,
        *,
        id: int,
    ) -> MessageModel:
        message_record: MessageModel = await self.mapper.select_by_id(id=id)
        if message_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        return message_record

    async def list_messages(
        self, req: ListMessagesRequest
    ) -> tuple[list[MessageModel], int]:
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
        if req.conversation_id is not None and req.conversation_id != "":
            filters[FilterOperators.EQ]["conversation_id"] = req.conversation_id
        if req.role is not None and req.role != "":
            filters[FilterOperators.EQ]["role"] = req.role
        if req.content is not None and req.content != "":
            filters[FilterOperators.EQ]["content"] = req.content
        if req.content_type is not None and req.content_type != "":
            filters[FilterOperators.EQ]["content_type"] = req.content_type
        if req.token_count is not None and req.token_count != "":
            filters[FilterOperators.EQ]["token_count"] = req.token_count
        if req.meta_data is not None and req.meta_data != "":
            filters[FilterOperators.EQ]["meta_data"] = req.meta_data
        if req.created_at is not None and req.created_at != "":
            filters[FilterOperators.EQ]["created_at"] = req.created_at
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

    

    async def create_message(self, req: CreateMessageRequest) -> MessageModel:
        message: MessageModel = MessageModel(**req.message.model_dump())
        return await self.save(data=message)

    async def update_message(self, req: UpdateMessageRequest) -> MessageModel:
        message_record: MessageModel = await self.retrieve_by_id(id=req.message.id)
        if message_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        message_model = MessageModel(**req.message.model_dump(exclude_unset=True))
        await self.modify_by_id(data=message_model)
        merged_data = {**message_record.model_dump(), **message_model.model_dump()}
        return MessageModel(**merged_data)

    async def delete_message(self, id: int) -> None:
        message_record: MessageModel = await self.retrieve_by_id(id=id)
        if message_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        await self.mapper.delete_by_id(id=id)

    async def batch_get_messages(self, ids: list[int]) -> list[MessageModel]:
        message_records = list[MessageModel] = await self.retrieve_by_ids(ids=ids)
        if message_records is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        if len(message_records) != len(ids):
            not_exits_ids = [id for id in ids if id not in message_records]
            raise BusinessException(
                BusinessErrorCode.RESOURCE_NOT_FOUND,
                f"{BusinessErrorCode.RESOURCE_NOT_FOUND.message}: {str(message_records)} != {str(not_exits_ids)}",
            )
        return message_records

    async def batch_create_messages(
        self,
        *,
        req: BatchCreateMessagesRequest,
    ) -> list[MessageModel]:
        message_list: list[CreateMessage] = req.messages
        if not message_list:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        data_list = [MessageModel(**message.model_dump()) for message in message_list]
        await self.mapper.batch_insert(data_list=data_list)
        return data_list

    async def batch_update_messages(
        self, req: BatchUpdateMessagesRequest
    ) -> list[MessageModel]:
        message: BatchUpdateMessage = req.message
        ids: list[int] = req.ids
        if not message or not ids:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        await self.mapper.batch_update_by_ids(
            ids=ids, data=message.model_dump(exclude_none=True)
        )
        return await self.mapper.select_by_ids(ids=ids)

    async def batch_patch_messages(
        self, req: BatchPatchMessagesRequest
    ) -> list[MessageModel]:
        messages: list[UpdateMessage] = req.messages
        if not messages:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        update_data: list[dict[str, Any]] = [
            message.model_dump(exclude_unset=True) for message in messages
        ]
        await self.mapper.batch_update(items=update_data)
        message_ids: list[int] = [message.id for message in messages]
        return await self.mapper.select_by_ids(ids=message_ids)

    async def batch_delete_messages(self, req: BatchDeleteMessagesRequest):
        ids: list[int] = req.ids
        await self.mapper.batch_delete_by_ids(ids=ids)

    async def export_messages_template(self) -> StreamingResponse:
        file_name = "message_import_tpl"
        return await excel_util.export_excel(
            schema=CreateMessage, file_name=file_name
        )

    async def export_messages(self, req: ExportMessagesRequest) -> StreamingResponse:
        ids: list[int] = req.ids
        message_list: list[MessageModel] = await self.mapper.select_by_ids(ids=ids)
        if message_list is None or len(message_list) == 0:
            logger.error(f"No messages found with ids {ids}")
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        message_page_list = [ExportMessage(**message.model_dump()) for message in message_list]
        file_name = "message_data_export"
        return await excel_util.export_excel(
            schema=ExportMessage, file_name=file_name, data_list=message_page_list
        )

    async def import_messages(self, req: ImportMessagesRequest) -> list[ImportMessage]:
        file = req.file
        contents = await file.read()
        import_df = pd.read_excel(io.BytesIO(contents))
        import_df = import_df.fillna("")
        message_records = import_df.to_dict(orient="records")
        if message_records is None or len(message_records) == 0:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        for record in message_records:
            for key, value in record.items():
                if value == "":
                    record[key] = None
        message_import_list = []
        for message_record in message_records:
            try:
                message_create = ImportMessage(**message_record)
                message_import_list.append(message_create)
            except ValidationError as e:
                valid_data = {
                    k: v
                    for k, v in message_record.items()
                    if k in ImportMessage.model_fields
                }
                message_create = ImportMessage.model_construct(**valid_data)
                message_create.err_msg = ValidateService.get_validate_err_msg(e)
                message_import_list.append(message_create)
                return message_import_list

        return message_import_list