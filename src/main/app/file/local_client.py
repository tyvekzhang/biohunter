# client.py
import requests
import hashlib
import os
import json
from typing import Optional

class ChunkedUploadClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.chunk_size = 1024 * 1024  # 1MB per chunk
    
    def calculate_file_md5(self, file_path: str) -> str:
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def calculate_chunk_md5(self, content: bytes) -> str:
        """计算分片MD5"""
        return hashlib.md5(content).hexdigest()
    
    def upload_file(self, file_path: str, resume_upload_id: Optional[str] = None):
        """
        上传文件
        :param file_path: 文件路径
        :param resume_upload_id: 如果提供，则恢复之前的上传
        """
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_md5 = self.calculate_file_md5(file_path)
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
        
        # 如果是恢复上传
        if resume_upload_id:
            upload_id = resume_upload_id
            # 获取上传状态
            response = requests.get(f"{self.base_url}/api/upload/status/{upload_id}")
            if response.status_code == 200:
                status = response.json()
                uploaded_chunks = set(status['uploaded_chunks'])
                print(f"恢复上传，已上传分片: {len(uploaded_chunks)}/{total_chunks}")
                
                # 如果是暂停状态，先恢复
                if status['status'] == 'paused':
                    requests.post(f"{self.base_url}/api/upload/resume/{upload_id}")
            else:
                print("无法获取上传状态，重新开始上传")
                resume_upload_id = None
                uploaded_chunks = set()
        else:
            uploaded_chunks = set()
        
        # 如果不是恢复上传，初始化新上传
        if not resume_upload_id:
            # 初始化上传
            init_data = {
                "filename": filename,
                "total_chunks": total_chunks,
                "file_size": file_size,
                "file_md5": file_md5
            }
            
            response = requests.post(
                f"{self.base_url}/api/upload/init",
                json=init_data
            )
            
            if response.status_code != 200:
                print(f"初始化上传失败: {response.text}")
                return False
            
            result = response.json()
            
            # 检查是否秒传成功
            if result['status'] == 'instant':
                print(f"秒传成功！文件路径: {result['file_path']}")
                return True
            
            upload_id = result['upload_id']
            print(f"上传ID: {upload_id}")
        
        # 上传分片
        with open(file_path, 'rb') as f:
            for chunk_number in range(total_chunks):
                # 跳过已上传的分片
                if chunk_number in uploaded_chunks:
                    print(f"分片 {chunk_number + 1}/{total_chunks} 已上传，跳过")
                    f.seek((chunk_number + 1) * self.chunk_size)
                    continue
                
                # 读取分片
                f.seek(chunk_number * self.chunk_size)
                chunk_data = f.read(self.chunk_size)
                chunk_md5 = self.calculate_chunk_md5(chunk_data)
                
                # 上传分片
                files = {'file': ('chunk', chunk_data)}
                data = {
                    'upload_id': upload_id,
                    'chunk_number': chunk_number,
                    'chunk_md5': chunk_md5
                }
                
                response = requests.post(
                    f"{self.base_url}/api/upload/chunk",
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    print(f"上传分片 {chunk_number + 1}/{total_chunks} 成功")
                else:
                    print(f"上传分片 {chunk_number + 1}/{total_chunks} 失败: {response.text}")
                    return False
        
        # 合并分片
        print("正在合并文件...")
        response = requests.post(f"{self.base_url}/api/upload/merge/{upload_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"文件上传成功！保存路径: {result['file_path']}")
            return True
        else:
            print(f"合并文件失败: {response.text}")
            return False
    
    def pause_upload(self, upload_id: str):
        """暂停上传"""
        response = requests.post(f"{self.base_url}/api/upload/pause/{upload_id}")
        if response.status_code == 200:
            print(f"上传已暂停")
            return True
        else:
            print(f"暂停失败: {response.text}")
            return False
    
    def cancel_upload(self, upload_id: str):
        """取消上传"""
        response = requests.delete(f"{self.base_url}/api/upload/cancel/{upload_id}")
        if response.status_code == 200:
            print(f"上传已取消")
            return True
        else:
            print(f"取消失败: {response.text}")
            return False
    
    def list_uploads(self, status: Optional[str] = None):
        """列出上传任务"""
        params = {'status': status} if status else {}
        response = requests.get(f"{self.base_url}/api/upload/list", params=params)
        if response.status_code == 200:
            return response.json()
        return []


# 使用示例
if __name__ == "__main__":
    client = ChunkedUploadClient()
    
    # 示例1: 普通上传
    print("=== 普通上传 ===")
    # client.upload_file("test_file.pdf")
    
    # 示例2: 秒传（相同文件）
    print("\n=== 秒传测试 ===")
    # client.upload_file("test_file.pdf")
    
    # 示例3: 断点续传
    print("\n=== 断点续传 ===")
    # 先获取之前暂停的上传ID
    paused_uploads = client.list_uploads(status='paused')
    if paused_uploads:
        upload_id = paused_uploads[0]['upload_id']
        print(f"恢复上传ID: {upload_id}")
        # client.upload_file("test_file.pdf", resume_upload_id=upload_id)