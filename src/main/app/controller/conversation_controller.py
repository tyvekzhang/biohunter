# SPDX-License-Identifier: MIT
"""Conversation REST Controller"""
from __future__ import annotations
from typing import Annotated

from fastlib.response import ListResponse
from fastapi import APIRouter, Query, Form
from starlette.responses import StreamingResponse

from src.main.app.mapper.conversation_mapper import conversationMapper
from src.main.app.model.conversation_model import ConversationModel
from src.main.app.schema.conversation_schema import (
    ListConversationsRequest,
    Conversation,
    CreateConversationRequest,
    ConversationDetail,
    UpdateConversationRequest,
    BatchDeleteConversationsRequest,
    BatchUpdateConversationsRequest,
    BatchUpdateConversationsResponse,
    BatchCreateConversationsRequest,
    BatchCreateConversationsResponse,
    ExportConversationsRequest,
    ImportConversationsResponse,
    BatchGetConversationsResponse,
    ImportConversationsRequest,
    ImportConversation, 
    BatchPatchConversationsRequest,
)
from src.main.app.service.impl.conversation_service_impl import ConversationServiceImpl
from src.main.app.service.conversation_service import ConversationService

conversation_router = APIRouter()
conversation_service: ConversationService = ConversationServiceImpl(mapper=conversationMapper)


@conversation_router.get("/conversations/{id}")
async def get_conversation(id: int) -> ConversationDetail:
    """
    Retrieve conversation details.

    Args:

        id: Unique ID of the conversation resource.

    Returns:

        ConversationDetail: The conversation object containing all its details.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have permission.
        HTTPException(404 Not Found): If the requested conversation does not exist.
    """
    conversation_record: ConversationModel = await conversation_service.get_conversation(id=id)
    return ConversationDetail(**conversation_record.model_dump())


@conversation_router.get("/conversations")
async def list_conversations(
    req: Annotated[ListConversationsRequest, Query()],
) -> ListResponse[Conversation]:
    """
    List conversations with pagination.

    Args:

        req: Request object containing pagination, filter and sort parameters.

    Returns:

        ListResponse: Paginated list of conversations and total count.

    Raises:

        HTTPException(403 Forbidden): If user don't have access rights.
    """
    conversation_records, total = await conversation_service.list_conversations(req=req)
    return ListResponse(records=conversation_records, total=total)


@conversation_router.post("/conversations")
async def creat_conversation(
    req: CreateConversationRequest,
) -> Conversation:
    """
    Create a new conversation.

    Args:

        req: Request object containing conversation creation data.

    Returns:

         Conversation: The conversation object.

    Raises:

        HTTPException(403 Forbidden): If the current user don't have access rights.
        HTTPException(409 Conflict): If the creation data already exists.
    """
    conversation: ConversationModel = await conversation_service.create_conversation(req=req)
    return Conversation(**conversation.model_dump())


@conversation_router.put("/conversations")
async def update_conversation(
    req: UpdateConversationRequest,
) -> Conversation:
    """
    Update an existing conversation.

    Args:

        req: Request object containing conversation update data.

    Returns:

        Conversation: The updated conversation object.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have update permissions.
        HTTPException(404 Not Found): If the conversation to update doesn't exist.
    """
    conversation: ConversationModel = await conversation_service.update_conversation(req=req)
    return Conversation(**conversation.model_dump())


@conversation_router.delete("/conversations/{id}")
async def delete_conversation(
    id: int,
) -> None:
    """
    Delete conversation by ID.

    Args:

        id: The ID of the conversation to delete.

    Raises:

        HTTPException(403 Forbidden): If the current user doesn't have access permissions.
        HTTPException(404 Not Found): If the conversation with given ID doesn't exist.
    """
    await conversation_service.delete_conversation(id=id)


@conversation_router.get("/conversations:batchGet")
async def batch_get_conversations(
    ids: list[int] = Query(..., description="List of conversation IDs to retrieve"),
) -> BatchGetConversationsResponse:
    """
    Retrieves multiple conversations by their IDs.

    Args:

        ids (list[int]): A list of conversation resource IDs.

    Returns:

        list[ConversationDetail]: A list of conversation objects matching the provided IDs.

    Raises:

        HTTPException(403 Forbidden): If the current user does not have access rights.
        HTTPException(404 Not Found): If one of the requested conversations does not exist.
    """
    conversation_records: list[ConversationModel] = await conversation_service.batch_get_conversations(ids)
    conversation_detail_list: list[ConversationDetail] = [
        ConversationDetail(**conversation_record.model_dump()) for conversation_record in conversation_records
    ]
    return BatchGetConversationsResponse(conversations=conversation_detail_list)


@conversation_router.post("/conversations:batchCreate")
async def batch_create_conversations(
    req: BatchCreateConversationsRequest,
) -> BatchCreateConversationsResponse:
    """
    Batch create conversations.

    Args:

        req (BatchCreateConversationsRequest): Request body containing a list of conversation creation items.

    Returns:

        BatchCreateConversationsResponse: Response containing the list of created conversations.

    Raises:

        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(409 Conflict): If any conversation creation data already exists.
    """

    conversation_records = await conversation_service.batch_create_conversations(req=req)
    conversation_list: list[Conversation] = [
        Conversation(**conversation_record.model_dump()) for conversation_record in conversation_records
    ]
    return BatchCreateConversationsResponse(conversations=conversation_list)


@conversation_router.post("/conversations:batchUpdate")
async def batch_update_conversations(
    req: BatchUpdateConversationsRequest,
) -> BatchUpdateConversationsResponse:
    """
    Batch update multiple conversations with the same changes.

    Args:

        req (BatchUpdateConversationsRequest): The batch update request data with ids.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated conversations.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify conversations
        HTTPException 404 (Not Found): If any specified conversation ID doesn't exist
    """
    conversation_records: list[ConversationModel] = await conversation_service.batch_update_conversations(req=req)
    conversation_list: list[Conversation] = [Conversation(**conversation.model_dump()) for conversation in conversation_records]
    return BatchUpdateConversationsResponse(conversations=conversation_list)


@conversation_router.post("/conversations:batchPatch")
async def batch_patch_conversations(
    req: BatchPatchConversationsRequest,
) -> BatchUpdateConversationsResponse:
    """
    Batch update multiple conversations with individual changes.

    Args:

        req (BatchPatchConversationsRequest): The batch patch request data.

    Returns:

        BatchUpdateBooksResponse: Contains the list of updated conversations.

    Raises:

        HTTPException 403 (Forbidden): If user lacks permission to modify conversations
        HTTPException 404 (Not Found): If any specified conversation ID doesn't exist
    """
    conversation_records: list[ConversationModel] = await conversation_service.batch_patch_conversations(req=req)
    conversation_list: list[Conversation] = [Conversation(**conversation.model_dump()) for conversation in conversation_records]
    return BatchUpdateConversationsResponse(conversations=conversation_list)


@conversation_router.post("/conversations:batchDelete")
async def batch_delete_conversations(
    req: BatchDeleteConversationsRequest,
) -> None:
    """
    Batch delete conversations.

    Args:
        req (BatchDeleteConversationsRequest): Request object containing delete info.

    Raises:
        HTTPException(404 Not Found): If any of the conversations do not exist.
        HTTPException(403 Forbidden): If user don't have access rights.
    """
    await conversation_service.batch_delete_conversations(req=req)


@conversation_router.get("/conversations:exportTemplate")
async def export_conversations_template() -> StreamingResponse:
    """
    Export the Excel template for conversation import.

    Returns:
        StreamingResponse: An Excel file stream containing the import template.

    Raises:
        HTTPException(403 Forbidden): If user don't have access rights.
    """

    return await conversation_service.export_conversations_template()


@conversation_router.get("/conversations:export")
async def export_conversations(
    req: ExportConversationsRequest = Query(...),
) -> StreamingResponse:
    """
    Export conversation data based on the provided conversation IDs.

    Args:
        req (ExportConversationsRequest): Query parameters specifying the conversations to export.

    Returns:
        StreamingResponse: A streaming response containing the generated Excel file.

    Raises:
        HTTPException(403 Forbidden): If the current user lacks access rights.
        HTTPException(404 Not Found ): If no matching conversations are found.
    """
    return await conversation_service.export_conversations(
        req=req,
    )

@conversation_router.post("/conversations:import")
async def import_conversations(
    req: ImportConversationsRequest = Form(...),
) -> ImportConversationsResponse:
    """
    Import conversations from an uploaded Excel file.

    Args:
        req (UploadFile): The Excel file containing conversation data to import.

    Returns:
        ImportConversationsResponse: List of successfully parsed conversation data.

    Raises:
        HTTPException(400 Bad Request): If the uploaded file is invalid or cannot be parsed.
        HTTPException(403 Forbidden): If the current user lacks access rights.
    """

    import_conversations_resp: list[ImportConversation] = await conversation_service.import_conversations(
        req=req
    )
    return ImportConversationsResponse(conversations=import_conversations_resp)