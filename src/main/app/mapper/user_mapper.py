# SPDX-License-Identifier: MIT
"""User mapper"""

from __future__ import annotations

from sqlmodel import select
from typing import Optional
from sqlmodel.ext.asyncio.session import AsyncSession

from fastlib.mapper.impl.base_mapper_impl import SqlModelMapper
from src.main.app.model.user_model import UserModel


class UserMapper(SqlModelMapper[UserModel]):

    async def select_by_username(
        self, *, username: str, db_session: Optional[AsyncSession] = None
    ) -> Optional[UserModel]:
        """
        Retrieve a record by username.
        """
        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model).where(self.model.username == username)
        )
        return result.one_or_none()

    async def select_by_username_list(
        self, *, username_list: list[str], db_session: Optional[AsyncSession] = None
    ) -> list[UserModel]:
        """
        Retrieve records by list of username.
        """
        db_session = db_session or self.db.session
        result = await db_session.exec(
            select(self.model).where(self.model.username.in_(username_list))
        )
        return result.all()



userMapper = UserMapper(UserModel)