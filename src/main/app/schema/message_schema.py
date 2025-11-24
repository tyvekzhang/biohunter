# SPDX-License-Identifier: MIT
"""Message schema"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field

from fastlib.request import ListRequest


class ListMessagesRequest(ListRequest):
    id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None
    token_count: Optional[int] = None
    meta_data: Optional[str] = None
    created_at: Optional[datetime] = None


class Message(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = 'text'
    token_count: Optional[int] = '0'
    meta_data: Optional[str] = None
    created_at: Optional[datetime] = CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP


class MessageDetail(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = 'text'
    token_count: Optional[int] = '0'
    meta_data: Optional[str] = None
    created_at: Optional[datetime] = CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP


class CreateMessage(BaseModel):
    conversation_id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = 'text'
    token_count: Optional[int] = '0'
    meta_data: Optional[str] = None


class CreateMessageRequest(BaseModel):
    message: CreateMessage = Field(alias="message")


class UpdateMessage(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = 'text'
    token_count: Optional[int] = '0'
    meta_data: Optional[str] = None


class UpdateMessageRequest(BaseModel):
    message: UpdateMessage = Field(alias="message")


class BatchGetMessagesResponse(BaseModel):
    messages: list[MessageDetail] = Field(default_factory=list, alias="messages")


class BatchCreateMessagesRequest(BaseModel):
    messages: list[CreateMessage] = Field(default_factory=list, alias="messages")


class BatchCreateMessagesResponse(BaseModel):
    messages: list[Message] = Field(default_factory=list, alias="messages")


class BatchUpdateMessage(BaseModel):
    conversation_id: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = 'text'
    token_count: Optional[int] = '0'
    meta_data: Optional[str] = None


class BatchUpdateMessagesRequest(BaseModel):
    ids: list[int]
    message: BatchUpdateMessage = Field(alias="message")


class BatchPatchMessagesRequest(BaseModel):
    messages: list[UpdateMessage] = Field(default_factory=list, alias="messages")


class BatchUpdateMessagesResponse(BaseModel):
     messages: list[Message] = Field(default_factory=list, alias="messages")


class BatchDeleteMessagesRequest(BaseModel):
    ids: list[int]


class ExportMessage(Message):
    pass


class ExportMessagesRequest(BaseModel):
    ids: list[int]


class ImportMessagesRequest(BaseModel):
    file: UploadFile


class ImportMessage(CreateMessage):
    err_msg: Optional[str] = Field(None, alias="errMsg")


class ImportMessagesResponse(BaseModel):
    messages: list[ImportMessage] = Field(default_factory=list, alias="messages")