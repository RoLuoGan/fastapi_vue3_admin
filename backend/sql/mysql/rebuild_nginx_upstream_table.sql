-- ============================================================
-- Nginx Upstream 表重建脚本
-- 功能：删除旧表并重新创建，支持多对多关系
-- ⚠️ 警告：此操作会删除所有现有数据，请先备份！
-- ============================================================

-- 步骤1: 备份现有数据（可选，但强烈建议）
-- 如果需要保留数据，请先执行以下语句备份：
-- CREATE TABLE `operations_nginx_upstream_backup` AS SELECT * FROM `operations_nginx_upstream`;
-- CREATE TABLE `operations_nginx_upstream_node_backup` AS SELECT * FROM `operations_nginx_upstream_node`;

-- 步骤2: 删除关联表（如果存在）
DROP TABLE IF EXISTS `operations_nginx_upstream_node`;

-- 步骤3: 删除主表（如果存在）
DROP TABLE IF EXISTS `operations_nginx_upstream`;

-- 步骤4: 重新创建主表（不包含 nginx_node_id 字段）
CREATE TABLE `operations_nginx_upstream` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `upstream` varchar(100) NOT NULL COMMENT 'upstream名称',
  `proxy_targets` text NOT NULL COMMENT '代理目标列表(JSON格式)',
  `upstream_template` text DEFAULT NULL COMMENT 'upstream模板（Jinja2格式）',
  `description` text DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_nginx_upstream_name` (`upstream`),
  KEY `ix_operations_nginx_upstream_creator_id` (`creator_id`),
  CONSTRAINT `fk_nginx_upstream_creator` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nginx Upstream表';

-- 步骤5: 创建关联表
CREATE TABLE `operations_nginx_upstream_node` (
  `nginx_upstream_id` int NOT NULL COMMENT 'Nginx Upstream ID',
  `node_id` int NOT NULL COMMENT 'Node ID',
  PRIMARY KEY (`nginx_upstream_id`, `node_id`),
  KEY `ix_operations_nginx_upstream_node_upstream_id` (`nginx_upstream_id`),
  KEY `ix_operations_nginx_upstream_node_node_id` (`node_id`),
  CONSTRAINT `fk_upstream_node_upstream` FOREIGN KEY (`nginx_upstream_id`) REFERENCES `operations_nginx_upstream` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_upstream_node_node` FOREIGN KEY (`node_id`) REFERENCES `operations_node` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nginx Upstream与节点关联表';

-- 步骤6: 数据恢复（如果之前有备份）
-- 如果有备份表 operations_nginx_upstream_backup，可以使用以下语句恢复数据：
-- 
-- -- 恢复主表数据（注意：需要处理重复的 upstream 名称）
-- INSERT INTO `operations_nginx_upstream` (`id`, `upstream`, `proxy_targets`, `upstream_template`, `description`, `created_at`, `updated_at`, `creator_id`)
-- SELECT `id`, `upstream`, `proxy_targets`, `upstream_template`, `description`, `created_at`, `updated_at`, `creator_id`
-- FROM `operations_nginx_upstream_backup`
-- WHERE `upstream` NOT IN (
--     SELECT `upstream` FROM `operations_nginx_upstream`
-- );
-- 
-- -- 恢复关联表数据
-- INSERT INTO `operations_nginx_upstream_node` (`nginx_upstream_id`, `node_id`)
-- SELECT `nginx_upstream_id`, `node_id`
-- FROM `operations_nginx_upstream_node_backup`;

-- 完成提示
SELECT "表重建完成！" AS message;
SELECT "如果之前有数据，请使用步骤6的恢复语句恢复数据。" AS message;

