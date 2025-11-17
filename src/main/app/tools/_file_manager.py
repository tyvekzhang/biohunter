from src.main.app.agent.context import get_current_message
from src.main.app.mapper.file_mapper import fileMapper
from src.main.app.service.file_service import FileService
from src.main.app.service.impl.file_service_impl import FileServiceImpl

file_service: FileService = FileServiceImpl(mapper=fileMapper)
INPUT_DIR = "/data/input/biohunter"
OUTPUT_DIR = "/data/output/biohunter"


async def file_context_aware() -> list[str]:
    message = get_current_message()
    target_directory = f"{INPUT_DIR}/{message.user_id}/{message.conversation_id}"
    file_info = await file_service.use_user_conversation_files(
        user_id=message.user_id,
        conversation_id=message.conversation_id,
        target_directory=target_directory,
    )
    return file_info
