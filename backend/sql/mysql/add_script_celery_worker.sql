-- MySQL Script Management and Celery Worker Tables
-- 脚本管理和Celery Worker节点管理表结构及菜单初始化

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET NAMES utf8mb4;
-- ----------------------------
-- Table structure for operations_celery_worker
-- ----------------------------
DROP TABLE IF EXISTS `operations_celery_worker`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_celery_worker` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `queue_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '执行队列名称',
  `queue_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '执行队列编码',
  `node_ip` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '节点IP',
  `node_hostname` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '节点主机名',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否在线(1:在线 0:离线)',
  `last_heartbeat` int DEFAULT NULL COMMENT '最后心跳时间戳',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_celery_worker_queue_ip` (`queue_code`,`node_ip`),
  KEY `ix_operations_celery_worker_queue_code` (`queue_code`),
  KEY `ix_operations_celery_worker_creator_id` (`creator_id`),
  CONSTRAINT `operations_celery_worker_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Celery Worker节点表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- ----------------------------
-- Table structure for operations_script
-- ----------------------------
DROP TABLE IF EXISTS `operations_script`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_script` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '脚本名称',
  `script_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '脚本类型(python/shell)',
  `content_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'text' COMMENT '脚本内容类型(text/local_path)',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '脚本内容或本地路径',
  `default_timeout` int NOT NULL DEFAULT '3600' COMMENT '默认超时时间(秒)',
  `queue_code` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '执行队列编码',
  `params_schema` text COLLATE utf8mb4_unicode_ci COMMENT '脚本参数JSON Schema',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用(1:启用 0:禁用)',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_script_name` (`name`),
  KEY `ix_operations_script_creator_id` (`creator_id`),
  CONSTRAINT `operations_script_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='脚本管理表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- ----------------------------
-- 初始化菜单数据
-- 获取运维管理父菜单ID
-- ----------------------------
SET @operations_parent_id = (SELECT id FROM system_menu WHERE route_name = 'Operations' LIMIT 1);

-- 脚本管理菜单
INSERT INTO `system_menu` (`name`, `type`, `icon`, `order`, `permission`, `route_name`, `route_path`, `component_path`, `status`, `keep_alive`, `hidden`, `always_show`, `title`, `params`, `affix`, `redirect`, `description`, `parent_id`, `created_at`, `updated_at`) VALUES
('脚本管理', 2, 'el-icon-Document', 8, 'operations:script:query', 'OperationsScript', '/operations/script', 'operations/script/index', 1, 1, 0, 0, '脚本管理', NULL, 0, NULL, '脚本管理', @operations_parent_id, NOW(), NOW());

SET @script_menu_id = LAST_INSERT_ID();

-- 脚本管理子菜单（按钮权限）
INSERT INTO `system_menu` (`name`, `type`, `icon`, `order`, `permission`, `route_name`, `route_path`, `component_path`, `status`, `keep_alive`, `hidden`, `always_show`, `title`, `params`, `affix`, `redirect`, `description`, `parent_id`, `created_at`, `updated_at`) VALUES
('查询脚本', 3, NULL, 1, 'operations:script:query', NULL, NULL, NULL, 1, 1, 0, 0, '查询脚本', NULL, 0, NULL, '查询脚本', @script_menu_id, NOW(), NOW()),
('创建脚本', 3, NULL, 2, 'operations:script:create', NULL, NULL, NULL, 1, 1, 0, 0, '创建脚本', NULL, 0, NULL, '创建脚本', @script_menu_id, NOW(), NOW()),
('修改脚本', 3, NULL, 3, 'operations:script:update', NULL, NULL, NULL, 1, 1, 0, 0, '修改脚本', NULL, 0, NULL, '修改脚本', @script_menu_id, NOW(), NOW()),
('删除脚本', 3, NULL, 4, 'operations:script:delete', NULL, NULL, NULL, 1, 1, 0, 0, '删除脚本', NULL, 0, NULL, '删除脚本', @script_menu_id, NOW(), NOW()),
('运行脚本', 3, NULL, 5, 'operations:script:run', NULL, NULL, NULL, 1, 1, 0, 0, '运行脚本', NULL, 0, NULL, '运行脚本', @script_menu_id, NOW(), NOW());

-- Celery节点管理菜单
INSERT INTO `system_menu` (`name`, `type`, `icon`, `order`, `permission`, `route_name`, `route_path`, `component_path`, `status`, `keep_alive`, `hidden`, `always_show`, `title`, `params`, `affix`, `redirect`, `description`, `parent_id`, `created_at`, `updated_at`) VALUES
('Celery节点管理', 2, 'el-icon-Cpu', 9, 'operations:celery_worker:query', 'OperationsCeleryWorker', '/operations/celery_worker', 'operations/celery_worker/index', 1, 1, 0, 0, 'Celery节点管理', NULL, 0, NULL, 'Celery Worker节点管理', @operations_parent_id, NOW(), NOW());

SET @celery_worker_menu_id = LAST_INSERT_ID();

-- Celery节点管理子菜单（按钮权限）
INSERT INTO `system_menu` (`name`, `type`, `icon`, `order`, `permission`, `route_name`, `route_path`, `component_path`, `status`, `keep_alive`, `hidden`, `always_show`, `title`, `params`, `affix`, `redirect`, `description`, `parent_id`, `created_at`, `updated_at`) VALUES
('查询Celery节点', 3, NULL, 1, 'operations:celery_worker:query', NULL, NULL, NULL, 1, 1, 0, 0, '查询Celery节点', NULL, 0, NULL, '查询Celery节点', @celery_worker_menu_id, NOW(), NOW()),
('创建Celery节点', 3, NULL, 2, 'operations:celery_worker:create', NULL, NULL, NULL, 1, 1, 0, 0, '创建Celery节点', NULL, 0, NULL, '创建Celery节点', @celery_worker_menu_id, NOW(), NOW()),
('修改Celery节点', 3, NULL, 3, 'operations:celery_worker:update', NULL, NULL, NULL, 1, 1, 0, 0, '修改Celery节点', NULL, 0, NULL, '修改Celery节点', @celery_worker_menu_id, NOW(), NOW()),
('删除Celery节点', 3, NULL, 4, 'operations:celery_worker:delete', NULL, NULL, NULL, 1, 1, 0, 0, '删除Celery节点', NULL, 0, NULL, '删除Celery节点', @celery_worker_menu_id, NOW(), NOW());

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Script completed
