# SPDX-License-Identifier: MIT
"""Conversation schema"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field, field_serializer

from fastlib.request import ListRequest


class ListConversationsRequest(ListRequest):
    id: Optional[int] = None
    title: Optional[str] = None
    created_at: Optional[str] = None
    update_at: Optional[str] = None


class Conversation(BaseModel):
    id: int
    title: str
    created_at: datetime
    update_at: datetime

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        return str(value)


class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    update_at: datetime


class CreateConversation(BaseModel):
    title: str


class CreateConversationRequest(BaseModel):
    conversation: CreateConversation = Field(alias="conversation")


class UpdateConversation(BaseModel):
    id: int
    title: str
    created_at: datetime
    update_at: datetime


class UpdateConversationRequest(BaseModel):
    conversation: UpdateConversation = Field(alias="conversation")


class BatchGetConversationsResponse(BaseModel):
    conversations: list[ConversationDetail] = Field(
        default_factory=list, alias="conversations"
    )


class BatchCreateConversationsRequest(BaseModel):
    conversations: list[CreateConversation] = Field(
        default_factory=list, alias="conversations"
    )


class BatchCreateConversationsResponse(BaseModel):
    conversations: list[Conversation] = Field(
        default_factory=list, alias="conversations"
    )


class BatchUpdateConversation(BaseModel):
    title: str
    created_at: datetime
    update_at: datetime


class BatchUpdateConversationsRequest(BaseModel):
    ids: list[int]
    conversation: BatchUpdateConversation = Field(alias="conversation")


class BatchPatchConversationsRequest(BaseModel):
    conversations: list[UpdateConversation] = Field(
        default_factory=list, alias="conversations"
    )


class BatchUpdateConversationsResponse(BaseModel):
    conversations: list[Conversation] = Field(
        default_factory=list, alias="conversations"
    )


class BatchDeleteConversationsRequest(BaseModel):
    ids: list[int]


class ExportConversation(Conversation):
    pass


class ExportConversationsRequest(BaseModel):
    ids: list[int]


class ImportConversationsRequest(BaseModel):
    file: UploadFile


class ImportConversation(CreateConversation):
    err_msg: Optional[str] = Field(None, alias="errMsg")


class ImportConversationsResponse(BaseModel):
    conversations: list[ImportConversation] = Field(
        default_factory=list, alias="conversations"
    )
