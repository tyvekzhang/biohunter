# app.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import hashlib
import json
import shutil
import uuid
from datetime import datetime
import aiofiles

app = FastAPI()

# 配置
UPLOAD_DIR = "uploads"
TEMP_DIR = "temp_uploads"
METADATA_DIR = "metadata"

# 创建必要的目录
for dir_path in [UPLOAD_DIR, TEMP_DIR, METADATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 数据模型
class InitUploadRequest(BaseModel):
    filename: str
    total_chunks: int
    file_size: int
    file_md5: str  # 整个文件的MD5，用于秒传

class ChunkUploadResponse(BaseModel):
    chunk_number: int
    status: str
    message: str

class UploadStatus(BaseModel):
    upload_id: str
    filename: str
    total_chunks: int
    uploaded_chunks: List[int]
    file_size: int
    file_md5: str
    status: str  # 'uploading', 'completed', 'paused', 'cancelled'
    created_at: str
    updated_at: str

# 工具函数
def calculate_file_md5(file_path: str) -> str:
    """计算文件的MD5值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def calculate_chunk_md5(content: bytes) -> str:
    """计算分片的MD5值"""
    return hashlib.md5(content).hexdigest()

def get_metadata_path(upload_id: str) -> str:
    """获取元数据文件路径"""
    return os.path.join(METADATA_DIR, f"{upload_id}.json")

def load_upload_metadata(upload_id: str) -> dict:
    """加载上传元数据"""
    metadata_path = get_metadata_path(upload_id)
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Upload ID not found")
    
    with open(metadata_path, 'r') as f:
        return json.load(f)

def save_upload_metadata(upload_id: str, metadata: dict):
    """保存上传元数据"""
    metadata_path = get_metadata_path(upload_id)
    metadata['updated_at'] = datetime.now().isoformat()
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def check_file_exists_by_md5(file_md5: str) -> Optional[str]:
    """通过MD5检查文件是否已存在（用于秒传）"""
    # 检查已完成的文件
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            if calculate_file_md5(file_path) == file_md5:
                return file_path
    return None

# API端点

@app.post("/api/upload/init")
async def init_upload(request: InitUploadRequest):
    """
    初始化分片上传，获取上传ID
    如果文件已存在（MD5相同），直接返回秒传成功
    """
    # 检查是否可以秒传
    existing_file = check_file_exists_by_md5(request.file_md5)
    if existing_file:
        return JSONResponse({
            "status": "instant",
            "message": "文件已存在，秒传成功",
            "file_path": existing_file,
            "upload_id": None
        })
    
    # 生成唯一的上传ID
    upload_id = str(uuid.uuid4())
    
    # 创建临时上传目录
    temp_upload_dir = os.path.join(TEMP_DIR, upload_id)
    os.makedirs(temp_upload_dir, exist_ok=True)
    
    # 保存上传元数据
    metadata = {
        "upload_id": upload_id,
        "filename": request.filename,
        "total_chunks": request.total_chunks,
        "uploaded_chunks": [],
        "file_size": request.file_size,
        "file_md5": request.file_md5,
        "status": "uploading",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    save_upload_metadata(upload_id, metadata)
    
    return JSONResponse({
        "status": "success",
        "upload_id": upload_id,
        "message": "上传初始化成功"
    })

@app.get("/api/upload/status/{upload_id}")
async def get_upload_status(upload_id: str):
    """获取上传状态，用于断点续传"""
    try:
        metadata = load_upload_metadata(upload_id)
        return UploadStatus(**metadata)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_number: int = Form(...),
    chunk_md5: str = Form(...),
    file: UploadFile = File(...)
):
    """上传单个分片"""
    try:
        # 加载元数据
        metadata = load_upload_metadata(upload_id)
        
        # 检查上传状态
        if metadata['status'] not in ['uploading', 'paused']:
            raise HTTPException(
                status_code=400, 
                detail=f"Upload is {metadata['status']}, cannot upload chunks"
            )
        
        # 检查分片号是否有效
        if chunk_number < 0 or chunk_number >= metadata['total_chunks']:
            raise HTTPException(status_code=400, detail="Invalid chunk number")
        
        # 检查分片是否已上传（用于断点续传）
        if chunk_number in metadata['uploaded_chunks']:
            return ChunkUploadResponse(
                chunk_number=chunk_number,
                status="exists",
                message="Chunk already uploaded"
            )
        
        # 读取分片内容
        content = await file.read()
        
        # 验证分片MD5
        actual_md5 = calculate_chunk_md5(content)
        if actual_md5 != chunk_md5:
            raise HTTPException(
                status_code=400,
                detail=f"Chunk MD5 mismatch. Expected: {chunk_md5}, Got: {actual_md5}"
            )
        
        # 保存分片
        temp_upload_dir = os.path.join(TEMP_DIR, upload_id)
        chunk_path = os.path.join(temp_upload_dir, f"chunk_{chunk_number:06d}")
        
        async with aiofiles.open(chunk_path, 'wb') as f:
            await f.write(content)
        
        # 更新元数据
        metadata['uploaded_chunks'].append(chunk_number)
        metadata['uploaded_chunks'].sort()
        save_upload_metadata(upload_id, metadata)
        
        return ChunkUploadResponse(
            chunk_number=chunk_number,
            status="success",
            message="Chunk uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/merge/{upload_id}")
async def merge_chunks(upload_id: str):
    """合并所有分片"""
    try:
        # 加载元数据
        metadata = load_upload_metadata(upload_id)
        
        # 检查是否所有分片都已上传
        if len(metadata['uploaded_chunks']) != metadata['total_chunks']:
            missing_chunks = set(range(metadata['total_chunks'])) - set(metadata['uploaded_chunks'])
            raise HTTPException(
                status_code=400,
                detail=f"Missing chunks: {sorted(missing_chunks)}"
            )
        
        # 合并分片
        temp_upload_dir = os.path.join(TEMP_DIR, upload_id)
        final_path = os.path.join(UPLOAD_DIR, metadata['filename'])
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(final_path) if os.path.dirname(final_path) else UPLOAD_DIR, exist_ok=True)
        
        # 合并文件
        with open(final_path, 'wb') as outfile:
            for chunk_number in range(metadata['total_chunks']):
                chunk_path = os.path.join(temp_upload_dir, f"chunk_{chunk_number:06d}")
                with open(chunk_path, 'rb') as infile:
                    outfile.write(infile.read())
        
        # 验证合并后文件的MD5
        final_md5 = calculate_file_md5(final_path)
        if final_md5 != metadata['file_md5']:
            os.remove(final_path)
            raise HTTPException(
                status_code=500,
                detail=f"File MD5 mismatch after merge. Expected: {metadata['file_md5']}, Got: {final_md5}"
            )
        
        # 清理临时文件
        shutil.rmtree(temp_upload_dir)
        
        # 更新元数据状态
        metadata['status'] = 'completed'
        metadata['final_path'] = final_path
        save_upload_metadata(upload_id, metadata)
        
        return JSONResponse({
            "status": "success",
            "message": "File merged successfully",
            "file_path": final_path,
            "file_md5": final_md5
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/pause/{upload_id}")
async def pause_upload(upload_id: str):
    """暂停上传"""
    try:
        metadata = load_upload_metadata(upload_id)
        
        if metadata['status'] != 'uploading':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause upload with status: {metadata['status']}"
            )
        
        metadata['status'] = 'paused'
        save_upload_metadata(upload_id, metadata)
        
        return JSONResponse({
            "status": "success",
            "message": "Upload paused",
            "uploaded_chunks": metadata['uploaded_chunks']
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/resume/{upload_id}")
async def resume_upload(upload_id: str):
    """恢复上传（断点续传）"""
    try:
        metadata = load_upload_metadata(upload_id)
        
        if metadata['status'] != 'paused':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume upload with status: {metadata['status']}"
            )
        
        metadata['status'] = 'uploading'
        save_upload_metadata(upload_id, metadata)
        
        # 返回已上传的分片信息，客户端可以从断点继续
        missing_chunks = set(range(metadata['total_chunks'])) - set(metadata['uploaded_chunks'])
        
        return JSONResponse({
            "status": "success",
            "message": "Upload resumed",
            "uploaded_chunks": metadata['uploaded_chunks'],
            "missing_chunks": sorted(missing_chunks)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/upload/cancel/{upload_id}")
async def cancel_upload(upload_id: str):
    """取消上传"""
    try:
        metadata = load_upload_metadata(upload_id)
        
        # 删除临时文件
        temp_upload_dir = os.path.join(TEMP_DIR, upload_id)
        if os.path.exists(temp_upload_dir):
            shutil.rmtree(temp_upload_dir)
        
        # 更新元数据状态
        metadata['status'] = 'cancelled'
        save_upload_metadata(upload_id, metadata)
        
        return JSONResponse({
            "status": "success",
            "message": "Upload cancelled and temporary files deleted"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload/list")
async def list_uploads(status: Optional[str] = None):
    """列出所有上传任务"""
    uploads = []
    
    for filename in os.listdir(METADATA_DIR):
        if filename.endswith('.json'):
            upload_id = filename[:-5]
            try:
                metadata = load_upload_metadata(upload_id)
                if status is None or metadata['status'] == status:
                    uploads.append(metadata)
            except:
                continue
    
    return uploads

@app.get("/api/files")
async def list_files():
    """列出所有已上传的文件"""
    files = []
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(file_path):
            files.append({
                "filename": filename,
                "size": os.path.getsize(file_path),
                "md5": calculate_file_md5(file_path),
                "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            })
    return files

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)