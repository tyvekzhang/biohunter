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
    DateTime,
    Integer,
    String,
)

from fastlib.utils.snowflake_util import snowflake_id


class FileBase(SQLModel):
    
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,sa_column_kwargs={"comment": "主键ID"}
    )
    file_uuid: str = Field(
        sa_column=Column(
            String(36),
            nullable=False,
            comment="文件标识符"
        )
    )
    storage_driver: str = Field(
        sa_column=Column(
            String(20),
            nullable=False,
            default='local',comment="存储类型(local, s3)"
        )
    )
    storage_path: str = Field(
        sa_column=Column(
            String(255),
            nullable=False,
            comment="文件路径"
        )
    )
    original_name: str = Field(
        sa_column=Column(
            String(255),
            nullable=False,
            comment="原始文件名"
        )
    )
    storage_name: str = Field(
        sa_column=Column(
            String(255),
            nullable=False,
            comment="存储文件名"
        )
    )
    file_hash: str = Field(
        sa_column=Column(
            String(64),
            nullable=False,
            comment="文件哈希值(SHA-256)"
        )
    )
    file_size: int = Field(
        sa_column=Column(
            Integer,
            nullable=False,
            comment="文件大小(字节)"
        )
    )
    file_extension: Optional[str] = Field(
        sa_column=Column(
            String(20),
            nullable=True,
            comment="文件扩展名 (例如: jpg, pdf)"
        )
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
    state: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="状态(0: 初始化, 1: 完成)"
        )
    )
    created_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),sa_column_kwargs={"comment": "创建时间"}
    )
    deleted_at: Optional[datetime] = Field(
        sa_column=Column(
            DateTime,
            nullable=True,
            comment="软删除时间"
        )
    )


class FileModel(FileBase, table=True):
    __tablename__ = "files"
    __table_args__ = (
    )