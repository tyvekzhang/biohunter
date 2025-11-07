CREATE TABLE `files` (
  `id` BIGINT UNSIGNED NOT NULL COMMENT '主键ID',
  `file_uuid` VARCHAR(36) NOT NULL COMMENT '文件标识符',
  `storage_driver` VARCHAR(20) NOT NULL DEFAULT 'local' COMMENT '存储类型(local, s3)',
  `storage_path` VARCHAR(255) NOT NULL COMMENT '文件路径',
  `original_name` VARCHAR(255) NOT NULL COMMENT '原始文件名',
  `storage_name` VARCHAR(255) NOT NULL COMMENT '存储文件名',
  `file_hash` VARCHAR(64) NOT NULL COMMENT '文件哈希值(SHA-256)',
  `file_size` BIGINT UNSIGNED NOT NULL COMMENT '文件大小(字节)',
  `file_extension` VARCHAR(20) NULL COMMENT '文件扩展名 (例如: jpg, pdf)',
  `user_id` BIGINT UNSIGNED NULL COMMENT '用户ID',
  `conversation_id` BIGINT UNSIGNED NULL COMMENT '对话ID',
  `state` TINYINT COMMENT '状态(0: 初始化, 1: 完成)',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `deleted_at` TIMESTAMP NULL COMMENT '软删除时间',
  PRIMARY KEY (`id`),
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件信息表';



