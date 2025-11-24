# SPDX-License-Identifier: MIT
"""Message REST Controller"""
from __future__ import annotations
from typing import Annotated

from fastlib.response import ListResponse
from fastapi import APIRouter, Query, Form
from starlette.responses import StreamingResponse

from src.main.app.mapper.message_mapper import messageMapper
from src.main.app.model.message_model import MessageModel
from src.main.app.schema.message_schema import (
    ListMessagesRequest,
    Message,
    CreateMessageRequest,
    MessageDetail,
    UpdateMessageRequest,
    BatchDeleteMessagesRequest,
    BatchUpdateMessagesRequest,
    BatchUpdateMessagesResponse,
    BatchCreateMessagesRequest,
    BatchCreateMessagesResponse,
    ExportMessagesRequest,
    ImportMessagesResponse,
    BatchGetMessagesResponse,
    ImportMessagesRequest,
    ImportMessage, BatchPatchMessagesRequest,
)
from src.main.app.service.impl.message_service_impl import MessageServiceImpl
from src.main.app.service.message_service import MessageService

message_router = APIRouter()
message_service: MessageService = MessageServiceImpl(mapper=messageMapper)


@message_router.get("/messages/{id}")
async def get_message(id: int) -> MessageDetail:
    """
    Retrieve message details.

    Args:

        id: Unique ID of the message resource.

    Returns:

        MessageDetail: The message object containing all its details.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have permission.
        HTTPException(404 Not Found): If the requested message does not exist.
    """
    message_record: MessageModel = await message_service.get_message(id=id)
    return MessageDetail(**message_record.model_dump())


@message_router.get("/messages")
async def list_messages(
    req: Annotated[ListMessagesRequest, Query()],
) -> ListResponse[Message]:
    """
    List messages with pagination.

    Args:

        req: Request object containing pagination, filter and sort parameters.

    Returns:

        ListResponse: Paginated list of messages and total count.

    Raises:

        HTTPException(403 Forbidden): If user don't have access rights.
    """
    message_records, total = await message_service.list_messages(req=req)
    return ListResponse(records=message_records, total=total)


@message_router.post("/messages")
async def creat_message(
    req: CreateMessageRequest,
) -> Message:
    """
    Create a new message.

    Args:

        req: Request object containing message creation data.

    Returns:

         Message: The message object.

    Raises:

        HTTPException(403 Forbidden): If the current user don't have access rights.
        HTTPException(409 Conflict): If the creation data already exists.
    """
    message: MessageModel = await message_service.create_message(req=req)
    return Message(**message.model_dump())


@message_router.put("/messages")
async def update_message(
    req: UpdateMessageRequest,
) -> Message:
    """
    Update an existing message.

    Args:

        req: Request object containing message update data.

    Returns:

        Message: The updated message object.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have update permissions.
        HTTPException(404 Not Found): If the message to update doesn't exist.
    """
    message: MessageModel = await message_service.update_message(req=req)
    return Message(**message.model_dump())


@message_router.delete("/messages/{id}")
async def delete_message(
    id: int,
) -> None:
    """
    Delete message by ID.

    Args:

        id: The ID of the message to delete.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have access permissions.
        HTTPException(404 Not Found): If the message with given ID doesn't exist.
    """
    await message_service.delete_message(id=id)


@message_router.get("/messages:batchGet")
async def batch_get_messages(
    ids: list[int] = Query(..., description="List of message IDs to retrieve"),
) -> BatchGetMessagesResponse:
    """
    Retrieves multiple messages by their IDs.

    Args:

        ids (list[int]): A list of message resource IDs.

    Returns:

        list[MessageDetail]: A list of message objects matching the provided IDs.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have access rights.
        HTTPException(404 Not Found): If one of the requested messages does not exist.
    """
    message_records: list[MessageModel] = await message_service.batch_get_messages(ids)
    message_detail_list: list[MessageDetail] = [
        MessageDetail(**message_record.model_dump()) for message_record in message_records
    ]
    return BatchGetMessagesResponse(messages=message_detail_list)


@message_router.post("/messages:batchCreate")
async def batch_create_messages(
    req: BatchCreateMessagesRequest,
) -> BatchCreateMessagesResponse:
    """
    Batch create messages.

    Args:

        req (BatchCreateMessagesRequest): Request body containing a list of message creation items.

    Returns:

        BatchCreateMessagesResponse: Response containing the list of created messages.

    Raises:

        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(409 Conflict): If any message creation data already exists.
    """

    message_records = await message_service.batch_create_messages(req=req)
    message_list: list[Message] = [
        Message(**message_record.model_dump()) for message_record in message_records
    ]
    return BatchCreateMessagesResponse(messages=message_list)


@message_router.post("/messages:batchUpdate")
async def batch_update_messages(
    req: BatchUpdateMessagesRequest,
) -> BatchUpdateMessagesResponse:
    """
    Batch update multiple messages with the same changes.

    Args:

        req (BatchUpdateMessagesRequest): The batch update request data with ids.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated messages.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify messages
        HTTPException 404 (Not Found): If any specified message ID doesn't exist
    """
    message_records: list[MessageModel] = await message_service.batch_update_messages(req=req)
    message_list: list[Message] = [Message(**message.model_dump()) for message in message_records]
    return BatchUpdateMessagesResponse(messages=message_list)


@message_router.post("/messages:batchPatch")
async def batch_patch_messages(
    req: BatchPatchMessagesRequest,
) -> BatchUpdateMessagesResponse:
    """
    Batch update multiple messages with individual changes.

    Args:

        req (BatchPatchMessagesRequest): The batch patch request data.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated messages.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify messages
        HTTPException 404 (Not Found): If any specified message ID doesn't exist
    """
    message_records: list[MessageModel] = await message_service.batch_patch_messages(req=req)
    message_list: list[Message] = [Message(**message.model_dump()) for message in message_records]
    return BatchUpdateMessagesResponse(messages=message_list)


@message_router.post("/messages:batchDelete")
async def batch_delete_messages(
    req: BatchDeleteMessagesRequest,
) -> None:
    """
    Batch delete messages.

    Args:
        req (BatchDeleteMessagesRequest): Request object containing delete info.

    Raises:
        HTTPException(404 Not Found): If any of the messages do not exist.
        HTTPException(403 Forbidden): If user don't have access rights.
    """
    await message_service.batch_delete_messages(req=req)


@message_router.get("/messages:exportTemplate")
async def export_messages_template() -> StreamingResponse:
    """
    Export the Excel template for message import.

    Returns:
        StreamingResponse: An Excel file stream containing the import template.

    Raises:
        HTTPException(403 Forbidden): If user don't have access rights.
    """

    return await message_service.export_messages_template()


@message_router.get("/messages:export")
async def export_messages(
    req: ExportMessagesRequest = Query(...),
) -> StreamingResponse:
    """
    Export message data based on the provided message IDs.

    Args:
        req (ExportMessagesRequest): Query parameters specifying the messages to export.

    Returns:
        StreamingResponse: A streaming response containing the generated Excel file.

    Raises:
        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(404 Not Found ): If no matching messages are found.
    """
    return await message_service.export_messages(
        req=req,
    )

@message_router.post("/messages:import")
async def import_messages(
    req: ImportMessagesRequest = Form(...),
) -> ImportMessagesResponse:
    """
    Import messages from an uploaded Excel file.

    Args:
        req (UploadFile): The Excel file containing message data to import.

    Returns:
        ImportMessagesResponse: List of successfully parsed message data.

    Raises:
        HTTPException(400 Bad Request): If the uploaded file is invalid or cannot be parsed.
        HTTPException(403 Forbidden): If the current user lacks access rights.
    """

    import_messages_resp: list[ImportMessage] = await message_service.import_messages(
        req=req
    )
    return ImportMessagesResponse(messages=import_messages_resp)