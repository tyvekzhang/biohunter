# SPDX-License-Identifier: MIT
"""User data model"""

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


class UserBase(SQLModel):
    
    id: int = Field(
        default_factory=snowflake_id,
        primary_key=True,
        nullable=False,
        sa_type=BigInteger,sa_column_kwargs={"comment": "主键"}
    )
    username: str = Field(
        sa_column=Column(
            String(32),
            nullable=False,
            comment="用户名"
        )
    )
    password: Optional[str] = Field(
        sa_column=Column(
            String(64),
            nullable=True,
            comment="密码"
        )
    )
    nickname: Optional[str] = Field(
        sa_column=Column(
            String(32),
            nullable=True,
            comment="昵称"
        )
    )
    avatar_url: Optional[str] = Field(
        sa_column=Column(
            String(64),
            nullable=True,
            comment="头像地址"
        )
    )
    status: Optional[int] = Field(
        sa_column=Column(
            Integer,
            nullable=True,
            comment="状态(0:停用,1:待审核,2:正常,3:已注销)"
        )
    )
    remark: Optional[str] = Field(
        sa_column=Column(
            String(255),
            nullable=True,
            comment="备注"
        )
    )
    created_at: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"comment": "创建时间"}
    )
    update_time: Optional[datetime] = Field(
        sa_type=DateTime,
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={
            "onupdate": lambda: datetime.now(timezone.utc),
            "comment": "更新时间",
        },
    )


class UserModel(UserBase, table=True):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="ix_sys_user_username"),
    )