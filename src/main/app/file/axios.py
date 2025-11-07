# <!DOCTYPE html>
# <html lang="zh-CN">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>分片上传客户端</title>
#     <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
#     <script src="https://cdn.jsdelivr.net/npm/spark-md5@3.0.2/spark-md5.min.js"></script>
# </head>
# <body>
#     <h1>分片上传示例</h1>
#     <input type="file" id="fileInput" />
#     <div id="progress"></div>
#     <button id="pauseBtn">暂停</button>
#     <button id="resumeBtn">恢复</button>
#     <button id="cancelBtn">取消</button>

#     <script>
#         // 分片上传类
#         class ChunkedUploader {
#             constructor(baseURL = 'http://localhost:8000') {
#                 this.baseURL = baseURL;
#                 this.CHUNK_SIZE = 5 * 1024 * 1024; // 5MB per chunk
#                 this.file = null;
#                 this.uploadId = null;
#                 this.uploadedChunks = new Set();
#                 this.isPaused = false;
#                 this.isCancelled = false;
#             }

#             // ==================== API接口调用 ====================

#             /**
#              * 1. 初始化上传，获取上传ID
#              * POST /api/upload/init
#              */
#             async initUpload(filename, totalChunks, fileSize, fileMd5) {
#                 const response = await axios.post(`${this.baseURL}/api/upload/init`, {
#                     filename: filename,
#                     total_chunks: totalChunks,
#                     file_size: fileSize,
#                     file_md5: fileMd5
#                 });
#                 return response.data;
#             }

#             /**
#              * 2. 上传单个分片
#              * POST /api/upload/chunk
#              */
#             async uploadChunk(uploadId, chunkNumber, chunkMd5, chunkData) {
#                 const formData = new FormData();
#                 formData.append('upload_id', uploadId);
#                 formData.append('chunk_number', chunkNumber);
#                 formData.append('chunk_md5', chunkMd5);
#                 formData.append('file', chunkData);

#                 const response = await axios.post(`${this.baseURL}/api/upload/chunk`, formData, {
#                     headers: {
#                         'Content-Type': 'multipart/form-data'
#                     },
#                     onUploadProgress: (progressEvent) => {
#                         // 单个分片的上传进度
#                         const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
#                         console.log(`分片 ${chunkNumber} 上传进度: ${percentCompleted}%`);
#                     }
#                 });
#                 return response.data;
#             }

#             /**
#              * 3. 合并所有分片
#              * POST /api/upload/merge/{upload_id}
#              */
#             async mergeChunks(uploadId) {
#                 const response = await axios.post(`${this.baseURL}/api/upload/merge/${uploadId}`);
#                 return response.data;
#             }

#             /**
#              * 4. 暂停上传
#              * POST /api/upload/pause/{upload_id}
#              */
#             async pauseUpload(uploadId) {
#                 const response = await axios.post(`${this.baseURL}/api/upload/pause/${uploadId}`);
#                 return response.data;
#             }

#             /**
#              * 5. 恢复上传（断点续传）
#              * POST /api/upload/resume/{upload_id}
#              */
#             async resumeUpload(uploadId) {
#                 const response = await axios.post(`${this.baseURL}/api/upload/resume/${uploadId}`);
#                 return response.data;
#             }

#             /**
#              * 6. 取消上传
#              * DELETE /api/upload/cancel/{upload_id}
#              */
#             async cancelUpload(uploadId) {
#                 const response = await axios.delete(`${this.baseURL}/api/upload/cancel/${uploadId}`);
#                 return response.data;
#             }

#             /**
#              * 7. 获取上传状态
#              * GET /api/upload/status/{upload_id}
#              */
#             async getUploadStatus(uploadId) {
#                 const response = await axios.get(`${this.baseURL}/api/upload/status/${uploadId}`);
#                 return response.data;
#             }

#             /**
#              * 8. 检查文件是否可以秒传
#              * POST /api/upload/check-instant
#              */
#             async checkInstantUpload(filename, totalChunks, fileSize, fileMd5) {
#                 const response = await axios.post(`${this.baseURL}/api/upload/check-instant`, {
#                     filename: filename,
#                     total_chunks: totalChunks,
#                     file_size: fileSize,
#                     file_md5: fileMd5
#                 });
#                 return response.data;
#             }

#             /**
#              * 9. 获取上传历史列表
#              * GET /api/upload/list
#              */
#             async getUploadList(status = null) {
#                 const params = status ? { status } : {};
#                 const response = await axios.get(`${this.baseURL}/api/upload/list`, { params });
#                 return response.data;
#             }

#             // ==================== 辅助方法 ====================

#             /**
#              * 计算文件MD5
#              */
#             async calculateFileMD5(file) {
#                 return new Promise((resolve, reject) => {
#                     const spark = new SparkMD5.ArrayBuffer();
#                     const fileReader = new FileReader();
#                     const chunks = Math.ceil(file.size / this.CHUNK_SIZE);
#                     let currentChunk = 0;

#                     fileReader.onload = (e) => {
#                         spark.append(e.target.result);
#                         currentChunk++;

#                         if (currentChunk < chunks) {
#                             loadNext();
#                         } else {
#                             resolve(spark.end());
#                         }
#                     };

#                     fileReader.onerror = reject;

#                     const loadNext = () => {
#                         const start = currentChunk * this.CHUNK_SIZE;
#                         const end = Math.min(start + this.CHUNK_SIZE, file.size);
#                         fileReader.readAsArrayBuffer(file.slice(start, end));
#                     };

#                     loadNext();
#                 });
#             }

#             /**
#              * 计算分片MD5
#              */
#             async calculateChunkMD5(chunk) {
#                 const arrayBuffer = await chunk.arrayBuffer();
#                 return SparkMD5.ArrayBuffer.hash(arrayBuffer);
#             }

#             // ==================== 主要上传流程 ====================

#             /**
#              * 完整的上传流程
#              */
#             async uploadFile(file) {
#                 this.file = file;
#                 const totalChunks = Math.ceil(file.size / this.CHUNK_SIZE);
                
#                 console.log('1. 计算文件MD5...');
#                 const fileMd5 = await this.calculateFileMD5(file);
#                 console.log(`文件MD5: ${fileMd5}`);

#                 console.log('2. 检查是否可以秒传...');
#                 const instantCheck = await this.checkInstantUpload(
#                     file.name,
#                     totalChunks,
#                     file.size,
#                     fileMd5
#                 );

#                 if (instantCheck.instant) {
#                     console.log('✅ 秒传成功！');
#                     return instantCheck;
#                 }

#                 console.log('3. 初始化上传...');
#                 const initResult = await this.initUpload(
#                     file.name,
#                     totalChunks,
#                     file.size,
#                     fileMd5
#                 );

#                 if (initResult.status === 'instant') {
#                     console.log('✅ 秒传成功！');
#                     return initResult;
#                 }

#                 this.uploadId = initResult.upload_id;
#                 console.log(`获取上传ID: ${this.uploadId}`);

#                 console.log('4. 开始分片上传...');
#                 await this.uploadChunks(totalChunks);

#                 if (!this.isPaused && !this.isCancelled) {
#                     console.log('5. 合并文件...');
#                     const mergeResult = await this.mergeChunks(this.uploadId);
#                     console.log('✅ 上传完成！', mergeResult);
#                     return mergeResult;
#                 }
#             }

#             /**
#              * 上传所有分片
#              */
#             async uploadChunks(totalChunks) {
#                 for (let i = 0; i < totalChunks; i++) {
#                     if (this.isPaused || this.isCancelled) {
#                         break;
#                     }

#                     // 跳过已上传的分片
#                     if (this.uploadedChunks.has(i)) {
#                         console.log(`分片 ${i} 已上传，跳过`);
#                         continue;
#                     }

#                     // 准备分片数据
#                     const start = i * this.CHUNK_SIZE;
#                     const end = Math.min(start + this.CHUNK_SIZE, this.file.size);
#                     const chunk = this.file.slice(start, end);
                    
#                     // 计算分片MD5
#                     const chunkMd5 = await this.calculateChunkMD5(chunk);
                    
#                     // 上传分片
#                     console.log(`上传分片 ${i + 1}/${totalChunks}`);
#                     const result = await this.uploadChunk(this.uploadId, i, chunkMd5, chunk);
                    
#                     if (result.status === 'success' || result.status === 'exists') {
#                         this.uploadedChunks.add(i);
#                         this.updateProgress(this.uploadedChunks.size, totalChunks);
#                     }
#                 }
#             }

#             /**
#              * 断点续传
#              */
#             async continueUpload(uploadId, file) {
#                 this.file = file;
#                 this.uploadId = uploadId;

#                 console.log('获取上传状态...');
#                 const status = await this.getUploadStatus(uploadId);
                
#                 // 恢复已上传的分片信息
#                 this.uploadedChunks = new Set(status.uploaded_chunks);
#                 console.log(`已上传分片: ${this.uploadedChunks.size}/${status.total_chunks}`);

#                 if (status.status === 'paused') {
#                     console.log('恢复上传...');
#                     await this.resumeUpload(uploadId);
#                 }

#                 // 继续上传剩余分片
#                 await this.uploadChunks(status.total_chunks);

#                 if (!this.isPaused && !this.isCancelled) {
#                     console.log('合并文件...');
#                     const mergeResult = await this.mergeChunks(uploadId);
#                     console.log('✅ 上传完成！', mergeResult);
#                     return mergeResult;
#                 }
#             }

#             /**
#              * 更新进度显示
#              */
#             updateProgress(uploaded, total) {
#                 const percent = Math.round((uploaded / total) * 100);
#                 document.getElementById('progress').innerHTML = 
#                     `上传进度: ${uploaded}/${total} (${percent}%)`;
#             }
#         }

#         // ==================== 使用示例 ====================

#         const uploader = new ChunkedUploader();

#         // 文件选择
#         document.getElementById('fileInput').addEventListener('change', async (e) => {
#             const file = e.target.files[0];
#             if (!file) return;

#             try {
#                 await uploader.uploadFile(file);
#             } catch (error) {
#                 console.error('上传失败:', error);
#             }
#         });

#         // 暂停按钮
#         document.getElementById('pauseBtn').addEventListener('click', async () => {
#             if (uploader.uploadId) {
#                 uploader.isPaused = true;
#                 const result = await uploader.pauseUpload(uploader.uploadId);
#                 console.log('已暂停:', result);
#             }
#         });

#         // 恢复按钮
#         document.getElementById('resumeBtn').addEventListener('click', async () => {
#             if (uploader.uploadId && uploader.file) {
#                 uploader.isPaused = false;
#                 await uploader.continueUpload(uploader.uploadId, uploader.file);
#             }
#         });

#         // 取消按钮
#         document.getElementById('cancelBtn').addEventListener('click', async () => {
#             if (uploader.uploadId) {
#                 uploader.isCancelled = true;
#                 const result = await uploader.cancelUpload(uploader.uploadId);
#                 console.log('已取消:', result);
#                 uploader.uploadId = null;
#                 uploader.uploadedChunks.clear();
#             }
#         });

#         // ==================== 其他功能示例 ====================

#         // 示例：获取所有上传历史
#         async function showUploadHistory() {
#             const uploads = await uploader.getUploadList();
#             console.log('上传历史:', uploads);
#         }

#         // 示例：获取暂停的上传任务
#         async function getPausedUploads() {
#             const uploads = await uploader.getUploadList('paused');
#             console.log('暂停的任务:', uploads);
#         }

#         // 示例：从特定上传ID恢复上传
#         async function resumeFromId(uploadId, file) {
#             await uploader.continueUpload(uploadId, file);
#         }
#     </script>
# </body>
# </html>