# SPDX-License-Identifier: MIT
"""Message data model"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import (
    SQLModel,
    Field,
    Column,
    DateTime,
    Index,
    UniqueConstraint,
    BigInteger,
    DateTime,
    Integer,
    String,
)

from fastlib.utils.snowflake_util import snowflake_id


class MessageBase(SQLModel):
    
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,sa_column_kwargs={"comment": "主键"}
    )
    conversation_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="对话ID"
        )
    )
    role: Optional[str] = Field(
        sa_column=Column(
            String,
            nullable=True,
            comment="角色"
        )
    )
    content: Optional[str] = Field(
        sa_column=Column(
            String,
            nullable=True,
            comment="内容"
        )
    )
    content_type: Optional[str] = Field(
        sa_column=Column(
            String(20),
            nullable=True,
            default='text',comment="内容类型"
        )
    )
    token_count: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            default='0',comment="token消耗"
        )
    )
    meta_data: Optional[str] = Field(
        sa_column=Column(
            String,
            nullable=True,
            comment="扩展字段"
        )
    )
    created_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),sa_column_kwargs={"comment": "创建时间"}
    )


class MessageModel(MessageBase, table=True):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_conv_created", "conversation_id, created_at"),
        {"comment": "对话消息表"},
    )