# SPDX-License-Identifier: MIT
"""File data model"""

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


class FileBase(SQLModel):
    
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,sa_column_kwargs={"comment": "主键"}
    )
    file_name: Optional[str] = Field(
        sa_column=Column(
            String(255),
            nullable=True,
            comment="文件名"
        )
    )
    format: Optional[str] = Field(
        sa_column=Column(
            String(255),
            nullable=True,
            comment="格式"
        )
    )
    file_size: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="文件大小"
        )
    )
    create_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),sa_column_kwargs={"comment": "创建时间"}
    )
    user_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="用户ID"
        )
    )
    conversation_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="对话ID"
        )
    )


class FileModel(FileBase, table=True):
    __tablename__ = "files"
    __table_args__ = (
    )