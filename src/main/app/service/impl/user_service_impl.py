# SPDX-License-Identifier: MIT
"""User domain service impl"""

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
from src.main.app.mapper.user_mapper import UserMapper
from src.main.app.model.user_model import UserModel
from src.main.app.schema.user_schema import (
    ListUsersRequest,
    User,
    CreateUserRequest,
    UpdateUserRequest,
    BatchDeleteUsersRequest,
    ExportUsersRequest,
    BatchCreateUsersRequest,
    CreateUser,
    BatchUpdateUsersRequest,
    UpdateUser,
    ImportUsersRequest,
    ImportUser,
    ExportUser,
    BatchPatchUsersRequest,
    BatchUpdateUser,
)
from src.main.app.service.user_service import UserService


class UserServiceImpl(BaseServiceImpl[UserMapper, UserModel], UserService):
    """
    Implementation of the UserService interface.
    """

    def __init__(self, mapper: UserMapper):
        """
        Initialize the UserServiceImpl instance.

        Args:
            mapper (UserMapper): The UserMapper instance to use for database operations.
        """
        super().__init__(mapper=mapper, model=UserModel)
        self.mapper = mapper

    async def get_user(
        self,
        *,
        id: int,
    ) -> UserModel:
        user_record: UserModel = await self.mapper.select_by_id(id=id)
        if user_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        return user_record

    async def list_users(
        self, req: ListUsersRequest
    ) -> tuple[list[UserModel], int]:
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
        if req.id is not None and req.id != "":
            filters[FilterOperators.EQ]["id"] = req.id
        if req.username is not None and req.username != "":
            filters[FilterOperators.LIKE]["username"] = req.username
        if req.password is not None and req.password != "":
            filters[FilterOperators.EQ]["password"] = req.password
        if req.nickname is not None and req.nickname != "":
            filters[FilterOperators.LIKE]["nickname"] = req.nickname
        if req.avatar_url is not None and req.avatar_url != "":
            filters[FilterOperators.EQ]["avatar_url"] = req.avatar_url
        if req.status is not None and req.status != "":
            filters[FilterOperators.EQ]["status"] = req.status
        if req.remark is not None and req.remark != "":
            filters[FilterOperators.EQ]["remark"] = req.remark
        if req.create_time is not None and req.create_time != "":
            filters[FilterOperators.EQ]["create_time"] = req.create_time
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

    

    async def create_user(self, req: CreateUserRequest) -> UserModel:
        user: UserModel = UserModel(**req.user.model_dump())
        return await self.save(data=user)

    async def update_user(self, req: UpdateUserRequest) -> UserModel:
        user_record: UserModel = await self.retrieve_by_id(id=req.user.id)
        if user_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        user_model = UserModel(**req.user.model_dump(exclude_unset=True))
        await self.modify_by_id(data=user_model)
        merged_data = {**user_record.model_dump(), **user_model.model_dump()}
        return UserModel(**merged_data)

    async def delete_user(self, id: int) -> None:
        user_record: UserModel = await self.retrieve_by_id(id=id)
        if user_record is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        await self.mapper.delete_by_id(id=id)

    async def batch_get_users(self, ids: list[int]) -> list[UserModel]:
        user_records = list[UserModel] = await self.retrieve_by_ids(ids=ids)
        if user_records is None:
            raise BusinessException(BusinessErrorCode.RESOURCE_NOT_FOUND)
        if len(user_records) != len(ids):
            not_exits_ids = [id for id in ids if id not in user_records]
            raise BusinessException(
                BusinessErrorCode.RESOURCE_NOT_FOUND,
                f"{BusinessErrorCode.RESOURCE_NOT_FOUND.message}: {str(user_records)} != {str(not_exits_ids)}",
            )
        return user_records

    async def batch_create_users(
        self,
        *,
        req: BatchCreateUsersRequest,
    ) -> list[UserModel]:
        user_list: list[CreateUser] = req.users
        if not user_list:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        data_list = [UserModel(**user.model_dump()) for user in user_list]
        await self.mapper.batch_insert(data_list=data_list)
        return data_list

    async def batch_update_users(
        self, req: BatchUpdateUsersRequest
    ) -> list[UserModel]:
        user: BatchUpdateUser = req.user
        ids: list[int] = req.ids
        if not user or not ids:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        await self.mapper.batch_update_by_ids(
            ids=ids, data=user.model_dump(exclude_none=True)
        )
        return await self.mapper.select_by_ids(ids=ids)

    async def batch_patch_users(
        self, req: BatchPatchUsersRequest
    ) -> list[UserModel]:
        users: list[UpdateUser] = req.users
        if not users:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        update_data: list[dict[str, Any]] = [
            user.model_dump(exclude_unset=True) for user in users
        ]
        await self.mapper.batch_update(items=update_data)
        user_ids: list[int] = [user.id for user in users]
        return await self.mapper.select_by_ids(ids=user_ids)

    async def batch_delete_users(self, req: BatchDeleteUsersRequest):
        ids: list[int] = req.ids
        await self.mapper.batch_delete_by_ids(ids=ids)

    async def export_users_template(self) -> StreamingResponse:
        file_name = "user_import_tpl"
        return await excel_util.export_excel(
            schema=CreateUser, file_name=file_name
        )

    async def export_users(self, req: ExportUsersRequest) -> StreamingResponse:
        ids: list[int] = req.ids
        user_list: list[UserModel] = await self.mapper.select_by_ids(ids=ids)
        if user_list is None or len(user_list) == 0:
            logger.error(f"No users found with ids {ids}")
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        user_page_list = [ExportUser(**user.model_dump()) for user in user_list]
        file_name = "user_data_export"
        return await excel_util.export_excel(
            schema=ExportUser, file_name=file_name, data_list=user_page_list
        )

    async def import_users(self, req: ImportUsersRequest) -> list[ImportUser]:
        file = req.file
        contents = await file.read()
        import_df = pd.read_excel(io.BytesIO(contents))
        import_df = import_df.fillna("")
        user_records = import_df.to_dict(orient="records")
        if user_records is None or len(user_records) == 0:
            raise BusinessException(BusinessErrorCode.PARAMETER_ERROR)
        for record in user_records:
            for key, value in record.items():
                if value == "":
                    record[key] = None
        user_import_list = []
        for user_record in user_records:
            try:
                user_create = ImportUser(**user_record)
                user_import_list.append(user_create)
            except ValidationError as e:
                valid_data = {
                    k: v
                    for k, v in user_record.items()
                    if k in ImportUser.model_fields
                }
                user_create = ImportUser.model_construct(**valid_data)
                user_create.err_msg = ValidateService.get_validate_err_msg(e)
                user_import_list.append(user_create)
                return user_import_list

        return user_import_list