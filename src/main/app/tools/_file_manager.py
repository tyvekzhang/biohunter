# import hashlib
# import json
# import logging
# import os
# import shutil
# from datetime import datetime
# from pathlib import Path
# from typing import List, Optional, Dict, Union

# import traceback
# import requests
# from pydantic import BaseModel, ValidationError
# from requests.exceptions import RequestException

# from biodeepdiscovery.cohort.agents.context import get_current_message
# from biodeepdiscovery.cohort import settings
# from biodeepdiscovery.cohort.tools.modules.schema import (
#     FileInfoVO,
#     AnalysisResult,
# )
# from biodeepdiscovery.models.agent import Message

# # 获取logger实例
# logger = logging.getLogger(__name__)



# class BizParams(BaseModel):
#     chat_id: str


# class FileItem(BaseModel):
#     id: int
#     filename: str
#     biz: str
#     biz_params: BizParams
#     size: int
#     hashcode: str
#     upload_at: datetime
#     user_id: str
#     status: str


# class DataResponse(BaseModel):
#     total: int
#     items: List[FileItem]


# class ApiResponse(BaseModel):
#     code: int
#     data: DataResponse
#     message: Optional[str]


# async def list_files_per_chat(
#     base_url: str = settings.file_service_url,
#     chat_id: str = None,
#     user_id: str = None,
#     page_size: int = 20,
#     page_number: int = 1,
#     timeout: float = 300.0,
# ) -> List[FileItem]:
#     """
#     Retrieve paginated list of files associated with a chat.

#     Args:
#         base_url: Base API URL (e.g., 'http://10.200.65.13:2015')
#         chat_id: Target chat ID to list files for
#         user_id: User ID for authentication
#         page_size: Number of items per page (default: 10)
#         page_number: Page number to retrieve (default: 1)
#         timeout: Request timeout in seconds (default: 10.0)

#     Returns:
#         ApiResponse: Parsed response containing file list

#     Raises:
#         RequestException: If network request fails
#         ValidationError: If response data doesn't match expected schema
#         ValueError: If API returns non-zero error code

#     Example:
#         >>> server_response = list_files_per_chat(
#         ...     base_url=settings.file_service_url,
#         ...     chat_id="01JY10AGP3EMJ6YRZYAY03573Q",
#         ...     user_id="1955228426376908801"
#         ... )
#     """
#     endpoint = f"{base_url.rstrip('/')}/listChatFiles"

#     message: Message = get_current_message()
#     if not chat_id:
#         chat_id = message.conversation_id
#     if not user_id:
#         user_id = message.user_id

#     try:
#         response = requests.get(
#             url=endpoint,
#             params={
#                 "chat_id": chat_id,
#                 "page_size": page_size,
#                 "page_number": page_number,
#             },
#             headers={"accept": "application/json", "X-User-Id": user_id},
#             timeout=timeout,
#         )
#         response.raise_for_status()  # Raises HTTPError for 4XX/5XX responses

#         response_json = response.json()
#         logger.info(f"response_json: {response_json}")
#         api_response = ApiResponse(**response_json)

#         if api_response.code != 0:
#             raise ValueError(
#                 f"API returned error code {api_response.code}: "
#                 f"{api_response.message or 'No error message'}"
#             )
#         file_item_list = api_response.data.items
#         result = []
#         for file_item in file_item_list:
#             if (
#                 file_item.filename.endswith(".png")
#                 or file_item.filename.endswith(".jpg")
#                 or file_item.filename.endswith(".pdf")
#                 or file_item.filename.endswith("metadata_details.csv")
#             ):
#                 continue
#             result.append(file_item)
#         return result

#     except RequestException as e:
#         raise RequestException(f"Network request failed: {str(e)}") from e
#     except ValidationError as e:
#         raise ValidationError(f"Response validation failed: {str(e)}") from e


# def download_file_by_id(
#     file_id: int,
#     base_url: str = settings.file_service_url,
#     user_id: str = None,
#     save_path: Optional[str] = None,
#     timeout: float = 300.0,
# ) -> Optional[str]:
#     """
#     Download a file from the API by its ID.

#     Args:
#         base_url: Base API URL (e.g., 'http://10.200.65.13:2015')
#         file_id: The ID of the file to download
#         user_id: User ID for authentication
#         save_path: Local path to save the file
#         timeout: Request timeout in seconds (default: 30.0)

#     Returns:
#         str: Path where the file was saved, or None if download failed

#     Raises:
#         RequestException: If the API request fails
#         ValueError: If the API returns an error or invalid response

#     Example:
#         >>> download_file_by_id(
#         ...     file_id=2277,
#         ...     base_url=settings.file_service_url,
#         ...     user_id="1955228426376908801",
#         ...     save_path="/path/to/save/file.ext"
#         ... )
#         '/path/to/save/file.ext'
#     """
#     message: Message = get_current_message()
#     if not user_id:
#         user_id = message.user_id

#     try:
#         endpoint = f"{base_url.rstrip('/')}/downloadFile"

#         response = requests.get(
#             url=endpoint,
#             params={"file_id": file_id},
#             headers={"accept": "application/json", "X-User-Id": user_id},
#             timeout=timeout,
#         )
#         response.raise_for_status()

#         with open(save_path, "wb") as f:
#             for chunk in response.iter_content(chunk_size=8192):
#                 f.write(chunk)

#         logger.info(f"File successfully downloaded to: {save_path}")
#         return save_path

#     except RequestException as e:
#         logger.error(f"Download failed: {str(e)}")
#         raise RequestException(f"File download failed: {str(e)}") from e
#     except Exception as e:
#         logger.error(f"Unexpected error during download: {str(e)}")
#         raise ValueError(f"Download process failed: {str(e)}") from e


# def calculate_hash(filepath):
#     with open(filepath, "rb") as f:
#         return hashlib.md5(f.read()).hexdigest()


# def upload_file(
#     file_path: str,
#     upload_url: str = f"{settings.file_service_url}/uploadSimpleFile",
#     user_id: int = None,
#     biz: str = "chat",
#     biz_params: Dict[str, str] = None,
# ) -> Dict[str, Union[str, int]]:
#     """
#     Upload a single file to the server

#     Args:
#         file_path: Local file path
#         upload_url: Upload API URL
#         user_id: User id
#         biz: Business type
#         biz_params: Business parameters

#     Returns:
#         Response data after successful upload (contains file URL and other info)

#     """
#     message: Message = get_current_message()
#     if biz_params is None:
#         biz_params = {"chat_id": str(message.conversation_id)}

#     filename = os.path.basename(file_path)
#     message: Message = get_current_message()
#     if not user_id:
#         user_id = message.user_id

#     # Prepare metadata
#     params = {
#         "filename": filename,
#         "size": os.path.getsize(file_path),
#         "hashcode": calculate_hash(file_path),
#         "biz": biz,
#         "biz_params": biz_params,
#     }

#     try:
#         with open(file_path, "rb") as f:
#             files = {
#                 "params": (None, json.dumps(params), "application/json"),
#                 "file": (filename, f, "application/octet-stream"),
#             }
#             response = requests.post(
#                 upload_url,
#                 files=files,
#                 headers={"X-User-Id": user_id},
#             )
#             response.raise_for_status()
#             response_json = response.json()
#             return response_json["data"]
#     except Exception as e:
#         raise Exception(f"File upload failed: {e}")


# async def file_context_aware() -> List[str]:
#     """
#     Downloads files and returns their paths with usage instructions.

#     Returns:
#         List of strings containing file paths and usage instructions.

#     Raises:
#         RuntimeError: If file listing or download fails.
#     """
#     file_path_list = []
#     file_info_tmp = "Uploaded file path: {} \nPlease use it if needed. \n"
#     message: Message = get_current_message()

#     try:
#         file_list: list[FileItem] = await list_files_per_chat()
#         for file in file_list:
#             try:
#                 # Create directory path
#                 dir_path = f"{settings.file_store_dir}/{str(message.user_id)}/{str(message.conversation_id)}"
#                 # Ensure directory exists
#                 Path(dir_path).mkdir(parents=True, exist_ok=True)

#                 file_path = os.path.join(dir_path, file.filename)
#                 download_file_by_id(file_id=file.id, save_path=file_path)
#                 file_path_list.append(file_info_tmp.format(file_path))
#             except Exception as e:
#                 logger.error(
#                     f"Failed to download file {file.filename}: {str(e)}"
#                 )
#                 continue

#         return file_path_list
#     except Exception as e:
#         logger.error(f"Failed to list files: {str(traceback.format_exc())}")
#         raise e


# def get_file_info(directory_path: str) -> List[FileInfoVO]:
#     """
#     Recursively scan a directory (excluding 'input' subdirectories) and return file information.

#     Args:
#         directory_path: Path to the directory to scan

#     Returns:
#         List of FileInfoVO objects containing file metadata.

#     Raises:
#         ValueError: If directory_path doesn't exist or isn't accessible.
#     """
#     if not Path(directory_path).exists():
#         raise ValueError(f"Directory not found: {directory_path}")

#     file_info_list = []

#     try:
#         for file_or_dir in Path(directory_path).iterdir():
#             try:
#                 if file_or_dir.is_dir():
#                     if file_or_dir.name == "input":
#                         continue
#                     file_info_list.extend(get_file_info(str(file_or_dir)))
#                 elif file_or_dir.is_file():
#                     file_name = file_or_dir.name
#                     file_format = (
#                         file_or_dir.suffix[1:]
#                         if file_or_dir.suffix
#                         else "unknown"
#                     )
#                     file_size = file_or_dir.stat().st_size

#                     file_info_list.append(
#                         FileInfoVO(
#                             fileName=file_name,
#                             format=file_format,
#                             fileSize=file_size,
#                             path=str(file_or_dir.absolute()),
#                         )
#                     )
#             except Exception as e:
#                 logger.warning(f"Skipping {file_or_dir}: {str(e)}")
#                 continue

#     except Exception as e:
#         logger.error(f"Failed to scan directory {directory_path}: {str(e)}")
#         raise RuntimeError("Directory scanning failed") from e

#     return file_info_list


# def result_file_transform(result_dir: str = None) -> AnalysisResult:
#     """
#     Transforms local file paths to remote file IDs by uploading files.

#     Args:
#         result_dir: Directory containing files to process

#     Returns:
#         List of FileInfoVO objects with updated remote file paths.

#     Raises:
#         RuntimeError: If file upload fails.
#     """
#     message: Message = get_current_message()
#     work_dir = f"{settings.file_store_dir}/{str(message.user_id)}/{str(message.conversation_id)}"
#     if result_dir is None:
#         result_dir = f"{work_dir}/output"
#     try:
#         file_info_list: List[FileInfoVO] = get_file_info(result_dir)
#         if len(file_info_list) == 0:
#             return None
#         # Upload the latest h5ad file
#         h5ad_files = []
#         upload_files = []
#         for file_info in file_info_list:
#             if file_info.fileName.lower().endswith(".h5ad"):
#                 h5ad_files.append(file_info)
#             else:
#                 upload_files.append(file_info)
#         if h5ad_files:
#             # 获取创建时间并排序
#             h5ad_with_time = [(f, os.path.getctime(f.path)) for f in h5ad_files]
#             latest_h5ad = max(h5ad_with_time, key=lambda x: x[1])[0]
#             upload_files.append(latest_h5ad)
#         file_info_result = []

#         for file_info in upload_files:
#             if file_info is None or file_info.path is None:
#                 continue
#             try:
#                 file_id = upload_file(file_info.path)
#                 file_info.fileId = file_id
#                 file_info_result.append(file_info)
#             except Exception as e:
#                 logger.error(
#                     f"Failed to upload file {file_info.path}: {str(e)}"
#                 )
#                 continue
#         if settings.delete_local_files:
#             shutil.rmtree(work_dir)
#         return AnalysisResult(data=file_info_result)
#     except Exception as e:
#         logger.error(f"File upload failed: {str(e)}")
#         raise RuntimeError("File upload failed") from e
