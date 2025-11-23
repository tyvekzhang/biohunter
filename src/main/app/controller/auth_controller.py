# Copyright (c) 2025 FastWeb and/or its affiliates. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Auth REST Controller"""

from datetime import timedelta
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastlib import security

from fastlib.schema import UserCredential
from src.main.app.mapper.user_mapper import userMapper
from src.main.app.model.user_model import UserModel
from src.main.app.service.impl.user_service_impl import UserServiceImpl

from src.main.app.service.user_service import UserService

auth_router = APIRouter()
user_service: UserService = UserServiceImpl(mapper=userMapper)


async def generate_tokens(user_id: int) -> UserCredential:
    """
    Generate access and refresh tokens for a user.

    Creates a long-lived token pair (access and refresh) with identical expiration.
    Both tokens are generated using the same user ID and expiration configuration.

    Args:

        user_id: User ID to generate tokens for

    Returns:

        UserCredential object containing access_token and refresh_token
    """
    token_expires = timedelta(days=3650)

    access_token = security.create_token(
        subject=user_id, token_type="Bearer", expires_delta=token_expires
    )

    # generate refresh token
    refresh_token = security.create_token(
        subject=user_id,
        token_type="Refresh",
        expires_delta=token_expires,
    )

    return UserCredential(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@auth_router.post("/auth:signIn")
async def signIn(
    req: OAuth2PasswordRequestForm = Depends(),
) -> UserCredential:
    fingerprint = req.username
    user = await userMapper.select_by_username(username=fingerprint)
    if user is None:
        user = UserModel(username=fingerprint)
        await userMapper.insert(data=user)
    return await generate_tokens(user.id)
