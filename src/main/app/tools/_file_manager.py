from src.main.app.agent.context import get_current_message
from src.main.app.mapper.file_mapper import fileMapper
from src.main.app.service.file_service import FileService
from src.main.app.service.impl.file_service_impl import FileServiceImpl

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from fastlib.db_engine import get_async_engine

engine = get_async_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

file_service: FileService = FileServiceImpl(mapper=fileMapper)
INPUT_DIR = "/data/biohunter/uploads"
OUTPUT_DIR = "/data/biohunter/output"


async def file_context_aware() -> list[str]:
    message = get_current_message()
    target_directory = f"{INPUT_DIR}/{message.user_id}/{message.conversation_id}/input"

    async with SessionFactory() as session:
        file_info = await file_service.use_user_conversation_files(
            user_id=message.user_id,
            conversation_id=message.conversation_id,
            target_directory=target_directory,
            session=session,
        )

    return file_info
