-- =====================================================
-- AI Agent 智能运维助手
-- 包含：表结构、默认规则数据、菜单配置
-- 创建时间：2026-01-09
-- =====================================================

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
-- =====================================================
-- 第一部分：删除现有表（按依赖关系顺序删除）
-- =====================================================

-- 先删除依赖表（有外键约束的表）
DROP TABLE IF EXISTS `operations_aiagent_message`;
DROP TABLE IF EXISTS `operations_aiagent_operation_log`;
DROP TABLE IF EXISTS `operations_aiagent_rule`;
-- 再删除被依赖的表
DROP TABLE IF EXISTS `operations_aiagent_session`;

-- =====================================================
-- 第二部分：创建表结构（按依赖关系顺序创建）
-- =====================================================

-- ----------------------------
-- Table structure for operations_aiagent_session
-- ----------------------------
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_aiagent_session` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `user_id` int NOT NULL COMMENT '用户ID',
  `session_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '会话名称',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active' COMMENT '会话状态',
  `context` json DEFAULT NULL COMMENT '会话上下文(JSON)',
  `llm_model` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '使用的LLM模型',
  `total_tokens` int NOT NULL DEFAULT '0' COMMENT '总消耗Token数',
  `ended_at` datetime DEFAULT NULL COMMENT '结束时间',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  KEY `ix_operations_aiagent_session_user_id` (`user_id`),
  KEY `ix_operations_aiagent_session_creator_id` (`creator_id`),
  CONSTRAINT `operations_aiagent_session_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `system_users` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `operations_aiagent_session_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI Agent会话表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- ----------------------------
-- Table structure for operations_aiagent_message
-- ----------------------------
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_aiagent_message` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` int NOT NULL COMMENT '会话ID',
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息角色',
  `content` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息内容',
  `tool_calls` json DEFAULT NULL COMMENT '工具调用记录(JSON)',
  `tool_call_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '工具调用ID',
  `tokens` int NOT NULL DEFAULT '0' COMMENT '消息Token数',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  KEY `ix_operations_aiagent_message_session_id` (`session_id`),
  KEY `ix_operations_aiagent_message_creator_id` (`creator_id`),
  CONSTRAINT `operations_aiagent_message_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `operations_aiagent_session` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `operations_aiagent_message_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI Agent消息表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- ----------------------------
-- Table structure for operations_aiagent_operation_log
-- ----------------------------
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_aiagent_operation_log` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `session_id` int NOT NULL COMMENT '会话ID',
  `operation_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '操作类型',
  `tool_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '工具名称',
  `target_resource` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '目标资源',
  `params` json DEFAULT NULL COMMENT '操作参数(JSON)',
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT '执行状态',
  `result` json DEFAULT NULL COMMENT '执行结果(JSON)',
  `error_message` text COLLATE utf8mb4_unicode_ci COMMENT '错误信息',
  `confirmed_by` int DEFAULT NULL COMMENT '确认人ID',
  `need_confirm` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否需要确认',
  `confirm_reason` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '需要确认的原因',
  `executed_at` datetime DEFAULT NULL COMMENT '执行时间',
  `confirmed_at` datetime DEFAULT NULL COMMENT '确认时间',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  KEY `ix_operations_aiagent_operation_log_session_id` (`session_id`),
  KEY `ix_operations_aiagent_operation_log_creator_id` (`creator_id`),
  CONSTRAINT `operations_aiagent_operation_log_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `operations_aiagent_session` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `operations_aiagent_operation_log_ibfk_2` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI Agent操作日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- ----------------------------
-- Table structure for operations_aiagent_rule
-- ----------------------------
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `operations_aiagent_rule` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `rule_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '规则名称',
  `rule_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '规则类型',
  `rule_config` json NOT NULL COMMENT '规则配置(JSON)',
  `priority` int NOT NULL DEFAULT '0' COMMENT '优先级(数字越大优先级越高)',
  `enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `description` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  KEY `ix_operations_aiagent_rule_creator_id` (`creator_id`),
  CONSTRAINT `operations_aiagent_rule_ibfk_1` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI Agent规则表';
/*!40101 SET character_set_client = @saved_cs_client */;

-- =====================================================
-- 第三部分：插入默认规则数据
-- =====================================================

LOCK TABLES `operations_aiagent_rule` WRITE;
/*!40000 ALTER TABLE `operations_aiagent_rule` DISABLE KEYS */;
INSERT INTO `operations_aiagent_rule` (`rule_name`, `rule_type`, `rule_config`, `priority`, `enabled`, `description`) VALUES
('删除操作确认', 'environment', '{\"operations\": [\"delete\", \"batch_delete\"], \"need_confirm\": true}', 100, 1, '所有删除操作必须确认'),
('生产环境确认', 'environment', '{\"environments\": [\"production\", \"prod\"], \"need_confirm\": true}', 90, 1, '生产环境操作必须确认'),
('批量操作限制', 'batch', '{\"max_count\": 10, \"need_confirm_threshold\": 5}', 80, 1, '批量操作超过5个资源需要确认'),
('高风险任务确认', 'environment', '{\"operations\": [\"deploy\", \"restart\", \"stop\", \"kill\"], \"need_confirm\": true}', 85, 1, '部署、重启等高风险任务需要确认');
/*!40000 ALTER TABLE `operations_aiagent_rule` ENABLE KEYS */;
UNLOCK TABLES;

-- =====================================================
-- 第四部分：插入菜单配置
-- =====================================================

-- 查找运维管理菜单ID
SET @operations_menu_id = (SELECT id FROM system_menu WHERE route_name = 'Operations' AND type = 1 LIMIT 1);

-- 检查是否已存在AI运维助手菜单
SET @existing_aiagent_menu = (SELECT id FROM system_menu WHERE route_name = 'OperationsAIAgent' LIMIT 1);

-- 如果不存在则插入
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 
    'AI运维助手', 2, 'el-icon-ChatDotRound', 10, 'operations:aiagent:query', 
    'OperationsAIAgent', '/operations/aiagent', 'operations/aiagent/index', 
    1, 1, 0, 0, 'AI运维助手', NULL, 0, NULL, 
    'AI智能运维管理助手', @operations_menu_id
WHERE @existing_aiagent_menu IS NULL;

-- 获取AI运维助手菜单ID
SET @aiagent_menu_id = (SELECT id FROM system_menu WHERE route_name = 'OperationsAIAgent' LIMIT 1);

-- 插入子菜单权限（如果不存在）
-- AI运维会话管理
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 'AI运维会话管理', 3, NULL, 1, 'operations:aiagent:session', NULL, NULL, NULL, 1, 1, 0, 0, 'AI会话管理', NULL, 0, NULL, '管理AI Agent会话', @aiagent_menu_id
WHERE NOT EXISTS (SELECT 1 FROM system_menu WHERE parent_id = @aiagent_menu_id AND permission = 'operations:aiagent:session');

-- AI运维智能对话
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 'AI运维智能对话', 3, NULL, 2, 'operations:aiagent:chat', NULL, NULL, NULL, 1, 1, 0, 0, 'AI智能对话', NULL, 0, NULL, '与AI Agent进行智能对话', @aiagent_menu_id
WHERE NOT EXISTS (SELECT 1 FROM system_menu WHERE parent_id = @aiagent_menu_id AND permission = 'operations:aiagent:chat');

-- AI运维操作确认
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 'AI运维操作确认', 3, NULL, 3, 'operations:aiagent:confirm', NULL, NULL, NULL, 1, 1, 0, 0, 'AI运维操作确认', NULL, 0, NULL, '确认AI Agent建议的操作', @aiagent_menu_id
WHERE NOT EXISTS (SELECT 1 FROM system_menu WHERE parent_id = @aiagent_menu_id AND permission = 'operations:aiagent:confirm');

-- AI运维人工接管
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 'AI运维人工接管', 3, NULL, 4, 'operations:aiagent:takeover', NULL, NULL, NULL, 1, 1, 0, 0, 'AI运维人工接管', NULL, 0, NULL, '人工接管AI Agent会话', @aiagent_menu_id
WHERE NOT EXISTS (SELECT 1 FROM system_menu WHERE parent_id = @aiagent_menu_id AND permission = 'operations:aiagent:takeover');

-- AI运维规则管理
INSERT INTO system_menu (
    name, type, icon, `order`, permission, route_name, route_path, 
    component_path, status, keep_alive, hidden, always_show, 
    title, params, affix, redirect, description, parent_id
)
SELECT 'AI运维规则管理', 3, NULL, 5, 'operations:aiagent:rule', NULL, NULL, NULL, 1, 1, 0, 0, 'AI运维规则管理', NULL, 0, NULL, '管理AI Agent操作规则', @aiagent_menu_id
WHERE NOT EXISTS (SELECT 1 FROM system_menu WHERE parent_id = @aiagent_menu_id AND permission = 'operations:aiagent:rule');


/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-09
