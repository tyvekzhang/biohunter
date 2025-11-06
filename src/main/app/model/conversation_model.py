# SPDX-License-Identifier: MIT
"""Conversation data model"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from sqlmodel import (
    SQLModel,
    Field,
    Column,
    DateTime,
    BigInteger,
    Integer,
    String,
)

from fastlib.utils.snowflake_util import snowflake_id


class ConversationBase(SQLModel):
    
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,sa_column_kwargs={"comment": "主键"}
    )
    user_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="用户id"
        )
    )
    title: Optional[str] = Field(
        sa_column=Column(
            String(255),
            nullable=True,
            comment="标题"
        )
    )
    create_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),sa_column_kwargs={"comment": "创建时间"}
    )
    update_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={
            "onupdate": lambda: datetime.now(timezone.utc), "comment": "更新时间",
        },
    )
    is_default: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="是否默认"
        )
    )


class ConversationModel(ConversationBase, table=True):
    __tablename__ = "conversations"
    __table_args__ = (
    )