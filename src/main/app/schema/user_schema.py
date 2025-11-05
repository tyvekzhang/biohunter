# SPDX-License-Identifier: MIT
"""User schema"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field

from fastlib.request import ListRequest


class ListUsersRequest(ListRequest):
    id: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None
    create_time: Optional[datetime] = None


class User(BaseModel):
    id: int
    username: str
    password: str
    nickname: str
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None
    create_time: Optional[datetime] = None


class UserDetail(BaseModel):
    id: int
    username: str
    password: str
    nickname: str
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None
    create_time: Optional[datetime] = None


class CreateUser(BaseModel):
    username: str
    password: str
    nickname: str
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class CreateUserRequest(BaseModel):
    user: CreateUser = Field(alias="user")


class UpdateUser(BaseModel):
    id: int
    username: str
    password: str
    nickname: str
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class UpdateUserRequest(BaseModel):
    user: UpdateUser = Field(alias="user")


class BatchGetUsersResponse(BaseModel):
    users: list[UserDetail] = Field(default_factory=list, alias="users")


class BatchCreateUsersRequest(BaseModel):
    users: list[CreateUser] = Field(default_factory=list, alias="users")


class BatchCreateUsersResponse(BaseModel):
    users: list[User] = Field(default_factory=list, alias="users")


class BatchUpdateUser(BaseModel):
    username: str
    password: str
    nickname: str
    avatar_url: Optional[str] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class BatchUpdateUsersRequest(BaseModel):
    ids: list[int]
    user: BatchUpdateUser = Field(alias="user")


class BatchPatchUsersRequest(BaseModel):
    users: list[UpdateUser] = Field(default_factory=list, alias="users")


class BatchUpdateUsersResponse(BaseModel):
     users: list[User] = Field(default_factory=list, alias="users")


class BatchDeleteUsersRequest(BaseModel):
    ids: list[int]


class ExportUser(User):
    pass


class ExportUsersRequest(BaseModel):
    ids: list[int]


class ImportUsersRequest(BaseModel):
    file: UploadFile


class ImportUser(CreateUser):
    err_msg: Optional[str] = Field(None, alias="errMsg")


class ImportUsersResponse(BaseModel):
    users: list[ImportUser] = Field(default_factory=list, alias="users")