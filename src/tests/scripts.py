import os
import hashlib
import json
from pathlib import Path

def get_files_info(directory_path):
    """获取目录下所有文件信息的简化版本"""
    
    files_info = []
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        if os.path.isfile(file_path):
            try:
                # 计算SHA-256
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(chunk)
                
                file_extension = Path(filename).suffix
                
                file_info = {
                    "original_name": filename,
                    "total_chunks": 0,
                    "file_size": os.path.getsize(file_path),
                    "file_hash": sha256_hash.hexdigest(),
                    "file_extension": file_extension[1:].lower() if file_extension else ""
                }
                files_info.append(file_info)
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
                continue
    
    return files_info

# 使用示例
directory = r"/data/dataset"
result = get_files_info(directory)
print(json.dumps(result, indent=2, ensure_ascii=False))