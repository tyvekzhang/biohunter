# SPDX-License-Identifier: MIT
"""Conversation data model"""

from __future__ import annotations

from datetime import datetime
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
    user_id: int = Field(
        sa_column=Column(
            Integer,
            nullable=False,
            comment="用户id"
        )
    )
    title: str = Field(
        sa_column=Column(
            String(255),
            nullable=False,
            comment="标题"
        )
    )
    create_at: Optional[datetime] = Field(
        sa_type=DateTime, default_factory=datetime.utcnow, sa_column_kwargs={"comment": "创建时间"}
    )
    update_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=datetime.utcnow,
        sa_column_kwargs={
            "onupdate": datetime.utcnow,"comment": "更新时间",
        },
    )


class ConversationModel(ConversationBase, table=True):
    __tablename__ = "conversations"
    __table_args__ = (
    )
