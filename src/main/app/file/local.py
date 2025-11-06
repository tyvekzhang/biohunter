import math
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, Form, Query, UploadFile
from fastapi import File as FastApiFile
from loguru import logger
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from app.common.context import Context
from app.common.exception import ServiceError
from app.db import crud
from app.db.orm import File, MultipartUpload, MultipartUploadPart
from app.schema.api import ApiResponse, ApiResponseCode
from app.schema.enum import FileStatus
from app.schema.file import FileId, InitMultipartUploadFileRequest, MultipartUploadFileStatus, UploadPartRequest
from app.service.directory import add_file_in_directory, create_or_get_directory, determine_directory_name_by_biz

router = APIRouter(tags=["multipart_upload"])


def get_upload_base_dir(ctx: Context) -> Path:
    """获取文件上传基础目录"""
    base_dir = Path(ctx.config.upload_dir) / "uploads"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_temp_upload_dir(ctx: Context, upload_id: str) -> Path:
    """获取临时分片目录"""
    temp_dir = Path(ctx.config.upload_dir) / "temp" / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_file_path(ctx: Context, user_id: str, file_id: int, filename: str) -> Path:
    """获取文件最终存储路径"""
    user_dir = get_upload_base_dir(ctx) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / f"{file_id}-{filename}"


@router.post("/initMultipartUploadFile", description="初始化分片上传任务")
def init_multipart_upload_file(
    request: InitMultipartUploadFileRequest = Body(), ctx: Context = Depends()
) -> ApiResponse[int]:
    with ctx.db.begin():
        # 插入File，获得file_id
        file_id = crud.insert_row(
            ctx.db,
            File,
            {
                "upload_at": datetime.now(timezone.utc).isoformat(),
                "biz": request.biz,
                "user_id": ctx.user_id,
                "filename": request.filename,
                "size": request.size,
                "hashcode": request.hashcode if request.hashcode is not None else "",
                "biz_params": request.biz_params,
                "status": FileStatus.uploading,
            },
            commit=False,
        )

        # 生成upload_id（本地使用UUID模拟）
        upload_id = str(uuid.uuid4())
        
        # 创建临时分片目录
        temp_dir = get_temp_upload_dir(ctx, upload_id)
        logger.info(f"created temp upload dir, {file_id=}, {upload_id=}, {temp_dir=}")

        # 确定文件最终存储路径
        file_path = get_file_path(ctx, ctx.user_id, file_id, request.filename)
        
        # 更新File的path
        local_path = f"file://{file_path.absolute()}"
        update_file_stmt = update(File).where(File.id == file_id).values(path=local_path)
        if ctx.db.execute(update_file_stmt).rowcount != 1:
            logger.error(f"update file path error, {file_id=}, {update_file_stmt=}")
            raise ServiceError.server_error("update file path error")

        # 处理目录
        dir_id = request.directory_id
        if dir_id is None:
            dir_name = determine_directory_name_by_biz(request.biz, request.biz_params)
            dir_id = create_or_get_directory(ctx.db, dir_name, ctx.user_id, commit=False)
        add_file_in_directory(ctx.db, file_id, dir_id, check_directory=True)

        # 插入MultipartUpload
        part_count = math.ceil(request.size / request.part_size)
        crud.insert_row(
            ctx.db,
            MultipartUpload,
            {"file_id": file_id, "upload_id": upload_id, "part_size": request.part_size, "part_count": part_count},
            commit=True,
        )

    return ApiResponse.success(file_id)


@router.post("/uploadFilePart", description="上传分片")
def upload_file_part(
    part: UploadFile = FastApiFile(description="上传的文件"),
    params: str = Form(description="文件参数JSON"),
    ctx: Context = Depends(),
) -> ApiResponse[int]:
    request = UploadPartRequest.model_validate_json(params)

    with ctx.db.begin():
        # 查询File和MultipartUpload，检查状态
        row = ctx.db.execute(
            select(
                File.id,
                File.status,
                File.path,
                MultipartUpload.upload_id,
                MultipartUpload.part_size,
                MultipartUpload.part_count,
            )
            .select_from(File)
            .join(MultipartUpload, File.id == MultipartUpload.file_id)
            .where(File.id == request.file_id)
        ).first()
        if row is None:
            raise ServiceError.param_error("file not found")
        file_id, status, local_path, upload_id, part_size, part_count = row
        if status != FileStatus.uploading:
            raise ServiceError.param_error("file is not uploading")
        if request.part_number > part_count or request.part_number <= 0:
            raise ServiceError.param_error("part number out of range")
        if request.part_number != part_count and part.size != part_size:
            raise ServiceError.param_error("part size mismatch")

        # 保存分片到临时目录
        temp_dir = get_temp_upload_dir(ctx, upload_id)
        part_file = temp_dir / f"part-{request.part_number:05d}"
        
        try:
            # 保存分片文件
            with part_file.open("wb") as f:
                shutil.copyfileobj(part.file, f)
            
            # 计算分片的MD5作为etag（简化实现）
            import hashlib
            with part_file.open("rb") as f:
                etag = hashlib.md5(f.read()).hexdigest()
            
            logger.info(f"local upload part success, {file_id=}, {upload_id=}, {request.part_number=}, {part_file=}")
        except Exception as e:
            logger.error(
                f"local upload part error, {file_id=}, {upload_id=}, {request.part_number=}, {e=}"
            )
            raise ServiceError.server_error("local upload part error")

        # 插入MultipartUploadPart
        try:
            ctx.db.execute(
                insert(MultipartUploadPart).values(
                    file_id=file_id, part_number=request.part_number, etag=etag
                )
            )
        except IntegrityError as e:
            logger.error(f"insert multipart upload part conflict, {file_id=}, {request.part_number=}, {e=}")
            raise ServiceError.param_error("part already uploaded")

    return ApiResponse.success(file_id)


@router.post("/completeMultipartUpload", description="完成分片上传任务，合并分片")
def complete_multipart_upload_file(request: FileId = Body(), ctx: Context = Depends()) -> ApiResponse[int]:
    with ctx.db.begin():
        # 查询File和MultipartUpload，检查状态
        row = ctx.db.execute(
            select(File.id, File.status, File.path, MultipartUpload.upload_id, MultipartUpload.part_count)
            .select_from(File)
            .join(MultipartUpload, File.id == MultipartUpload.file_id)
            .where(File.id == request.file_id)
        ).first()
        if row is None:
            raise ServiceError.param_error("file not found")
        file_id, status, local_path, upload_id, part_count = row
        if status != FileStatus.uploading:
            raise ServiceError.param_error("file is not uploading")

        # 查询MultipartUploadPart，检查所有分片是否上传完成
        uploaded_parts = ctx.db.execute(
            select(MultipartUploadPart.part_number, MultipartUploadPart.etag)
            .where(MultipartUploadPart.file_id == file_id)
            .order_by(MultipartUploadPart.part_number.asc())
        ).all()
        if len(uploaded_parts) < part_count:
            raise ServiceError.param_error("some parts not uploaded")

        # 更新File状态为merging
        result = ctx.db.execute(update(File).where(File.id == file_id).values(status=FileStatus.merging))
        if result.rowcount != 1:
            logger.error(f"update file status error, {file_id=}, {result=}")
            raise ServiceError.server_error("update file status error")
        logger.info(f"updated file status, {file_id=}, status={FileStatus.merging}")

    with ctx.db.begin():
        # 从path提取实际文件路径
        file_path = Path(local_path.replace("file://", ""))
        temp_dir = get_temp_upload_dir(ctx, upload_id)
        
        # 合并分片文件
        try:
            # 确保目标目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 按顺序合并所有分片
            with file_path.open("wb") as output_file:
                for part_number, _ in uploaded_parts:
                    part_file = temp_dir / f"part-{part_number:05d}"
                    if not part_file.exists():
                        raise FileNotFoundError(f"Part file not found: {part_file}")
                    
                    with part_file.open("rb") as input_file:
                        shutil.copyfileobj(input_file, output_file)
            
            # 删除临时分片目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            file_status = FileStatus.ok
            logger.info(f"local complete multipart upload success, {file_id=}, {file_path=}, {upload_id=}")
        except Exception as e:
            file_status = FileStatus.error
            logger.error(
                f"local complete multipart upload error, {file_id=}, {file_path=}, {upload_id=}, {e=}"
            )

        # 更新File状态
        result = ctx.db.execute(update(File).where(File.id == file_id).values(status=file_status))
        if result.rowcount != 1:
            logger.error(f"update file status error, {file_id=}, {result=}")
            raise ServiceError.server_error("update file status error")
        logger.info(f"updated file status, {file_id=}, status={file_status}")

        # 删除MultipartUpload和MultipartUploadPart
        result = ctx.db.execute(delete(MultipartUpload).where(MultipartUpload.file_id == file_id))
        if result.rowcount == 1:
            logger.info(f"deleted multipart upload, {file_id=}")
        else:
            logger.error(f"delete multipart upload error, {file_id=}, {result=}")
        result = ctx.db.execute(delete(MultipartUploadPart).where(MultipartUploadPart.file_id == file_id))
        if result.rowcount >= 1:
            logger.info(f"deleted multipart upload parts, {file_id=}, deleted_rows={result.rowcount}")
        else:
            logger.error(f"delete multipart upload parts error, {file_id=}, {result=}")

    # 根据File状态返回结果
    if file_status != FileStatus.ok:
        raise ServiceError.server_error("local complete multipart upload error")
    return ApiResponse.success(file_id)


@router.post("/abortMultipartUpload", description="中止分片上传任务")
def abort_multipart_upload_file(request: FileId = Body(), ctx: Context = Depends()) -> ApiResponse[int]:
    with ctx.db.begin():
        # 查询File和MultipartUpload，检查状态
        row = ctx.db.execute(
            select(File.id, File.status, File.path, MultipartUpload.upload_id)
            .select_from(File)
            .join(MultipartUpload, File.id == MultipartUpload.file_id)
            .where(File.id == request.file_id)
        ).first()
        if row is None:
            raise ServiceError.param_error("file not found")
        file_id, status, local_path, upload_id = row
        if status != FileStatus.uploading:
            raise ServiceError.param_error("file is not uploading")

        # 删除临时分片目录
        temp_dir = get_temp_upload_dir(ctx, upload_id)
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            logger.info(f"local abort multipart upload success, {file_id=}, {upload_id=}, {temp_dir=}")
        except Exception as e:
            logger.error(f"local abort multipart upload error, {file_id=}, {upload_id=}, {e=}")
            # 继续执行，不中断流程

        # 更新File状态
        result = ctx.db.execute(update(File).where(File.id == file_id).values(status=FileStatus.error))
        if result.rowcount != 1:
            logger.error(f"update file status error, {file_id=}, {result=}")
            raise ServiceError.server_error("update file status error")
        logger.info(f"updated file status, {file_id=}, status={FileStatus.error}")

        # 删除MultipartUpload和MultipartUploadPart
        result = ctx.db.execute(delete(MultipartUpload).where(MultipartUpload.file_id == file_id))
        if result.rowcount == 1:
            logger.info(f"deleted multipart upload, {file_id=}")
        else:
            logger.error(f"delete multipart upload error, {file_id=}, {result=}")
        result = ctx.db.execute(delete(MultipartUploadPart).where(MultipartUploadPart.file_id == file_id))
        if result.rowcount >= 1:
            logger.info(f"deleted multipart upload parts, {file_id=}, deleted_rows={result.rowcount}")
        else:
            logger.error(f"delete multipart upload parts error, {file_id=}, {result=}")

    return ApiResponse.success(file_id)


@router.get("/getMultipartUploadFileStatus", description="获取分片上传任务状态")
def get_multipart_upload_file_status(
    file_id: int = Query(description="文件ID"), ctx: Context = Depends()
) -> ApiResponse[MultipartUploadFileStatus]:
    # 此函数不需要修改，因为只查询数据库
    with ctx.db.begin():
        # 查询File和MultipartUpload，检查状态
        row = ctx.db.execute(
            select(File.id, File.status, MultipartUpload.part_size, MultipartUpload.part_count)
            .select_from(File)
            .join(MultipartUpload, File.id == MultipartUpload.file_id)
            .where(File.id == file_id)
        ).first()
        if row is None:
            raise ServiceError.param_error("file not found")
        file_id, status, part_size, part_count = row

        uploaded_parts, remaining_parts = None, None
        if status == FileStatus.uploading:
            # 查询MultipartUploadPart，获取已上传分片
            uploaded_parts = list(
                ctx.db.execute(
                    select(MultipartUploadPart.part_number)
                    .where(MultipartUploadPart.file_id == file_id)
                    .order_by(MultipartUploadPart.part_number.asc())
                )
                .scalars()
                .all()
            )
            remaining_parts = [i for i in range(1, part_count + 1) if i not in uploaded_parts]

        code = ApiResponseCode.SERVER_ERROR if status == FileStatus.error else ApiResponseCode.SUCCESS
        message = "merge uploaded file error" if status == FileStatus.error else None
        return ApiResponse(
            code=code,
            message=message,
            data=MultipartUploadFileStatus(
                file_id=file_id,
                status=status,
                part_size=part_size,
                uploaded_parts=uploaded_parts,
                remaining_parts=remaining_parts,
            ),
        )