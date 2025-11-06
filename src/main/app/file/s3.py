# import math
# from datetime import datetime, timezone
# from typing import List

# from fastapi import APIRouter, Body, Depends, Form, Query, UploadFile
# from fastapi import File as FastApiFile
# from loguru import logger
# from minio import Minio
# from minio.datatypes import Part
# from sqlalchemy import delete, insert, select, update
# from sqlalchemy.exc import IntegrityError

# from app.common.context import Context
# from app.common.exception import ServiceError
# from app.db import crud
# from app.db.orm import File, MultipartUpload, MultipartUploadPart
# from app.schema.api import ApiResponse, ApiResponseCode
# from app.schema.enum import FileStatus
# from app.schema.file import FileId, InitMultipartUploadFileRequest, MultipartUploadFileStatus, UploadPartRequest
# from app.service.directory import add_file_in_directory, create_or_get_directory, determine_directory_name_by_biz

# router = APIRouter(tags=["multipart_upload"])


# def get_minio_client(ctx: Context) -> Minio:
#     """获取MinIO客户端"""
#     return Minio(
#         ctx.config.minio_endpoint,
#         access_key=ctx.config.minio_access_key,
#         secret_key=ctx.config.minio_secret_key,
#         secure=ctx.config.minio_use_ssl
#     )


# def get_minio_key(user_id: str, file_id: int, filename: str) -> str:
#     """生成MinIO对象键"""
#     return f"{user_id}/{file_id}-{filename}"


# @router.post("/initMultipartUploadFile", description="初始化分片上传任务")
# def init_multipart_upload_file(
#     request: InitMultipartUploadFileRequest = Body(), ctx: Context = Depends()
# ) -> ApiResponse[int]:
#     with ctx.db.begin():
#         # 插入File，获得file_id
#         file_id = crud.insert_row(
#             ctx.db,
#             File,
#             {
#                 "upload_at": datetime.now(timezone.utc).isoformat(),
#                 "biz": request.biz,
#                 "user_id": ctx.user_id,
#                 "filename": request.filename,
#                 "size": request.size,
#                 "hashcode": request.hashcode if request.hashcode is not None else "",
#                 "biz_params": request.biz_params,
#                 "status": FileStatus.uploading,
#             },
#             commit=False,
#         )

#         # 调用MinIO创建分片上传任务，获得upload_id
#         minio_client = get_minio_client(ctx)
#         object_key = get_minio_key(ctx.user_id, file_id, request.filename)
        
#         try:
#             upload_id = minio_client._create_multipart_upload(
#                 ctx.config.minio_bucket,
#                 object_key,
#                 {},  # metadata
#             )
#             logger.info(f"minio init multipart upload success, {file_id=}, {object_key=}, {upload_id=}")
#         except Exception as e:
#             logger.error(f"minio init multipart upload error, {file_id=}, {object_key=}, {e=}")
#             raise ServiceError.server_error("minio init multipart upload error")

#         # 更新File的path
#         minio_path = f"minio://{ctx.config.minio_bucket}/{object_key}"
#         update_file_stmt = update(File).where(File.id == file_id).values(path=minio_path)
#         if ctx.db.execute(update_file_stmt).rowcount != 1:
#             logger.error(f"update file path error, {file_id=}, {update_file_stmt=}")
#             raise ServiceError.server_error("update file path error")

#         # 处理目录
#         dir_id = request.directory_id
#         if dir_id is None:
#             dir_name = determine_directory_name_by_biz(request.biz, request.biz_params)
#             dir_id = create_or_get_directory(ctx.db, dir_name, ctx.user_id, commit=False)
#         add_file_in_directory(ctx.db, file_id, dir_id, check_directory=True)

#         # 插入MultipartUpload
#         part_count = math.ceil(request.size / request.part_size)
#         crud.insert_row(
#             ctx.db,
#             MultipartUpload,
#             {"file_id": file_id, "upload_id": upload_id, "part_size": request.part_size, "part_count": part_count},
#             commit=True,
#         )

#     return ApiResponse.success(file_id)


# @router.post("/uploadFilePart", description="上传分片")
# def upload_file_part(
#     part: UploadFile = FastApiFile(description="上传的文件"),
#     params: str = Form(description="文件参数JSON"),
#     ctx: Context = Depends(),
# ) -> ApiResponse[int]:
#     request = UploadPartRequest.model_validate_json(params)

#     with ctx.db.begin():
#         # 查询File和MultipartUpload，检查状态
#         row = ctx.db.execute(
#             select(
#                 File.id,
#                 File.status,
#                 File.path,
#                 MultipartUpload.upload_id,
#                 MultipartUpload.part_size,
#                 MultipartUpload.part_count,
#             )
#             .select_from(File)
#             .join(MultipartUpload, File.id == MultipartUpload.file_id)
#             .where(File.id == request.file_id)
#         ).first()
#         if row is None:
#             raise ServiceError.param_error("file not found")
#         file_id, status, minio_path, upload_id, part_size, part_count = row
#         if status != FileStatus.uploading:
#             raise ServiceError.param_error("file is not uploading")
#         if request.part_number > part_count or request.part_number <= 0:
#             raise ServiceError.param_error("part number out of range")
#         if request.part_number != part_count and part.size != part_size:
#             raise ServiceError.param_error("part size mismatch")

#         # 从path提取object_key
#         object_key = minio_path.replace(f"minio://{ctx.config.minio_bucket}/", "")
        
#         # MinIO上传分片
#         minio_client = get_minio_client(ctx)
#         try:
#             etag = minio_client._upload_part(
#                 ctx.config.minio_bucket,
#                 object_key,
#                 upload_id,
#                 request.part_number,
#                 part.file,
#                 part.size
#             )
#             logger.info(f"minio upload part success, {file_id=}, {object_key=}, {upload_id=}, {request.part_number=}")
#         except Exception as e:
#             logger.error(
#                 f"minio upload part error, {file_id=}, {object_key=}, {upload_id=}, {request.part_number=}, {e=}"
#             )
#             raise ServiceError.server_error("minio upload part error")

#         # 插入MultipartUploadPart
#         try:
#             ctx.db.execute(
#                 insert(MultipartUploadPart).values(
#                     file_id=file_id, part_number=request.part_number, etag=etag
#                 )
#             )
#         except IntegrityError as e:
#             logger.error(f"insert multipart upload part conflict, {file_id=}, {request.part_number=}, {e=}")
#             raise ServiceError.param_error("part already uploaded")

#     return ApiResponse.success(file_id)


# @router.post("/completeMultipartUpload", description="完成分片上传任务，合并分片")
# def complete_multipart_upload_file(request: FileId = Body(), ctx: Context = Depends()) -> ApiResponse[int]:
#     with ctx.db.begin():
#         # 查询File和MultipartUpload，检查状态
#         row = ctx.db.execute(
#             select(File.id, File.status, File.path, MultipartUpload.upload_id, MultipartUpload.part_count)
#             .select_from(File)
#             .join(MultipartUpload, File.id == MultipartUpload.file_id)
#             .where(File.id == request.file_id)
#         ).first()
#         if row is None:
#             raise ServiceError.param_error("file not found")
#         file_id, status, minio_path, upload_id, part_count = row
#         if status != FileStatus.uploading:
#             raise ServiceError.param_error("file is not uploading")

#         # 查询MultipartUploadPart，检查所有分片是否上传完成
#         uploaded_parts = ctx.db.execute(
#             select(MultipartUploadPart.part_number, MultipartUploadPart.etag)
#             .where(MultipartUploadPart.file_id == file_id)
#             .order_by(MultipartUploadPart.part_number.asc())
#         ).all()
#         if len(uploaded_parts) < part_count:
#             raise ServiceError.param_error("some parts not uploaded")

#         # 更新File状态为merging
#         result = ctx.db.execute(update(File).where(File.id == file_id).values(status=FileStatus.merging))
#         if result.rowcount != 1:
#             logger.error(f"update file status error, {file_id=}, {result=}")
#             raise ServiceError.server_error("update file status error")
#         logger.info(f"updated file status, {file_id=}, status={FileStatus.merging}")

#     with ctx.db.begin():
#         # 从path提取object_key
#         object_key = minio_path.replace(f"minio://{ctx.config.minio_bucket}/", "")
        
#         # 调用MinIO完成分片上传任务，合并分片
#         minio_client = get_minio_client(ctx)
#         parts = [Part(part_number, etag) for part_number, etag in uploaded_parts]
        
#         try:
#             minio_client._complete_multipart_upload(
#                 ctx.config.minio_bucket,
#                 object_key,
#                 upload_id,
#                 parts
#             )
#             file_status = FileStatus.ok
#             logger.info(f"minio complete multipart upload success, {file_id=}, {object_key=}, {upload_id=}")
#         except Exception as e:
#             file_status = FileStatus.error
#             logger.error(
#                 f"minio complete multipart upload error, {file_id=}, {object_key=}, {upload_id=}, {e=}"
#             )

#         # 更新File状态
#         result = ctx.db.execute(update(File).where(File.id == file_id).values(status=file_status))
#         if result.rowcount != 1:
#             logger.error(f"update file status error, {file_id=}, {result=}")
#             raise ServiceError.server_error("update file status error")
#         logger.info(f"updated file status, {file_id=}, status={file_status}")

#         # 删除MultipartUpload和MultipartUploadPart
#         result = ctx.db.execute(delete(MultipartUpload).where(MultipartUpload.file_id == file_id))
#         if result.rowcount == 1:
#             logger.info(f"deleted multipart upload, {file_id=}")
#         else:
#             logger.error(f"delete multipart upload error, {file_id=}, {result=}")
#         result = ctx.db.execute(delete(MultipartUploadPart).where(MultipartUploadPart.file_id == file_id))
#         if result.rowcount >= 1:
#             logger.info(f"deleted multipart upload parts, {file_id=}, deleted_rows={result.rowcount}")
#         else:
#             logger.error(f"delete multipart upload parts error, {file_id=}, {result=}")

#     # 根据File状态返回结果
#     if file_status != FileStatus.ok:
#         raise ServiceError.server_error("minio complete multipart upload error")
#     return ApiResponse.success(file_id)


# @router.post("/abortMultipartUpload", description="中止分片上传任务")
# def abort_multipart_upload_file(request: FileId = Body(), ctx: Context = Depends()) -> ApiResponse[int]:
#     with ctx.db.begin():
#         # 查询File和MultipartUpload，检查状态
#         row = ctx.db.execute(
#             select(File.id, File.status, File.path, MultipartUpload.upload_id)
#             .select_from(File)
#             .join(MultipartUpload, File.id == MultipartUpload.file_id)
#             .where(File.id == request.file_id)
#         ).first()
#         if row is None:
#             raise ServiceError.param_error("file not found")
#         file_id, status, minio_path, upload_id = row
#         if status != FileStatus.uploading:
#             raise ServiceError.param_error("file is not uploading")

#         # 从path提取object_key
#         object_key = minio_path.replace(f"minio://{ctx.config.minio_bucket}/", "")
        
#         # 调用MinIO中止分片上传任务
#         minio_client = get_minio_client(ctx)
#         try:
#             minio_client._abort_multipart_upload(
#                 ctx.config.minio_bucket,
#                 object_key,
#                 upload_id
#             )
#             logger.info(f"minio abort multipart upload success, {file_id=}, {object_key=}, {upload_id=}")
#         except Exception as e:
#             logger.error(f"minio abort multipart upload error, {file_id=}, {object_key=}, {upload_id=}, {e=}")
#             raise ServiceError.server_error("minio abort multipart upload error")

#         # 更新File状态
#         result = ctx.db.execute(update(File).where(File.id == file_id).values(status=FileStatus.error))
#         if result.rowcount != 1:
#             logger.error(f"update file status error, {file_id=}, {result=}")
#             raise ServiceError.server_error("update file status error")
#         logger.info(f"updated file status, {file_id=}, status={FileStatus.error}")

#         # 删除MultipartUpload和MultipartUploadPart
#         result = ctx.db.execute(delete(MultipartUpload).where(MultipartUpload.file_id == file_id))
#         if result.rowcount == 1:
#             logger.info(f"deleted multipart upload, {file_id=}")
#         else:
#             logger.error(f"delete multipart upload error, {file_id=}, {result=}")
#         result = ctx.db.execute(delete(MultipartUploadPart).where(MultipartUploadPart.file_id == file_id))
#         if result.rowcount >= 1:
#             logger.info(f"deleted multipart upload parts, {file_id=}, deleted_rows={result.rowcount}")
#         else:
#             logger.error(f"delete multipart upload parts error, {file_id=}, {result=}")

#     return ApiResponse.success(file_id)


# @router.get("/getMultipartUploadFileStatus", description="获取分片上传任务状态")
# def get_multipart_upload_file_status(
#     file_id: int = Query(description="文件ID"), ctx: Context = Depends()
# ) -> ApiResponse[MultipartUploadFileStatus]:
#     # 此函数不需要修改，因为只查询数据库
#     with ctx.db.begin():
#         # 查询File和MultipartUpload，检查状态
#         row = ctx.db.execute(
#             select(File.id, File.status, MultipartUpload.part_size, MultipartUpload.part_count)
#             .select_from(File)
#             .join(MultipartUpload, File.id == MultipartUpload.file_id)
#             .where(File.id == file_id)
#         ).first()
#         if row is None:
#             raise ServiceError.param_error("file not found")
#         file_id, status, part_size, part_count = row

#         uploaded_parts, remaining_parts = None, None
#         if status == FileStatus.uploading:
#             # 查询MultipartUploadPart，获取已上传分片
#             uploaded_parts = list(
#                 ctx.db.execute(
#                     select(MultipartUploadPart.part_number)
#                     .where(MultipartUploadPart.file_id == file_id)
#                     .order_by(MultipartUploadPart.part_number.asc())
#                 )
#                 .scalars()
#                 .all()
#             )
#             remaining_parts = [i for i in range(1, part_count + 1) if i not in uploaded_parts]

#         code = ApiResponseCode.SERVER_ERROR if status == FileStatus.error else ApiResponseCode.SUCCESS
#         message = "merge uploaded file error" if status == FileStatus.error else None
#         return ApiResponse(
#             code=code,
#             message=message,
#             data=MultipartUploadFileStatus(
#                 file_id=file_id,
#                 status=status,
#                 part_size=part_size,
#                 uploaded_parts=uploaded_parts,
#                 remaining_parts=remaining_parts,
#             ),
#         )