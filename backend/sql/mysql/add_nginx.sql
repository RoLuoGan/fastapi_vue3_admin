-- Nginx Upstream 表结构
-- 用于存储 Nginx Upstream 配置信息

DROP TABLE IF EXISTS `operations_nginx_upstream`;

CREATE TABLE `operations_nginx_upstream` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `upstream` varchar(100) NOT NULL COMMENT 'upstream名称',
  `proxy_targets` text NOT NULL COMMENT '代理目标列表(JSON格式)',
  `nginx_node_id` int NOT NULL COMMENT 'Nginx节点ID',
  `upstream_template` text DEFAULT NULL COMMENT 'upstream模板（Jinja2格式）',
  `health_check_enabled` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否启用健康检查',
  `health_status` varchar(20) DEFAULT NULL COMMENT '健康状态(healthy:健康, unhealthy:不健康, unknown:未知)',
  `last_check_time` int DEFAULT NULL COMMENT '最后检查时间（Unix时间戳）',
  `description` text DEFAULT NULL COMMENT '备注/描述',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `creator_id` int DEFAULT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_nginx_upstream_name_node` (`upstream`, `nginx_node_id`),
  KEY `ix_operations_nginx_upstream_nginx_node_id` (`nginx_node_id`),
  KEY `ix_operations_nginx_upstream_creator_id` (`creator_id`),
  CONSTRAINT `fk_nginx_upstream_node` FOREIGN KEY (`nginx_node_id`) REFERENCES `operations_node` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_nginx_upstream_creator` FOREIGN KEY (`creator_id`) REFERENCES `system_users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Nginx Upstream表';

-- 为 operations_service 表添加 endpoint_port 字段
ALTER TABLE `operations_service` 
ADD COLUMN `endpoint_port` int DEFAULT NULL COMMENT '服务端口号(用于Nginx代理)' AFTER `current_package_version`;

-- Nginx Upstream 管理菜单
-- 获取运维管理父菜单ID
SET @parentMenuId = (SELECT id FROM `system_menu` WHERE `name` = '运维管理' AND `type` = 1 LIMIT 1);

-- 检查父菜单是否存在，如果不存在则插入，如果存在则获取ID
SET @nginxUpstreamMenuId = (SELECT id FROM `system_menu` WHERE `name` = 'Nginx Upstream管理' AND `type` = 2 LIMIT 1);

-- 如果菜单不存在，则插入
INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT 
  'Nginx Upstream管理',
  2,
  7,
  1,
  'operations:nginx_upstream:query',
  'el-icon-Connection',
  'NginxUpstream',
  '/operations/nginx_upstream',
  'operations/nginx_upstream/index',
  NULL,
  0,
  1,
  0,
  'Nginx Upstream管理',
  NULL,
  0,
  @parentMenuId,
  'Nginx Upstream配置管理',
  now(),
  now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = 'Nginx Upstream管理' AND `type` = 2);

-- 获取父菜单ID（如果刚才插入了，则使用LAST_INSERT_ID，否则使用之前查询的ID）
SET @nginxUpstreamMenuId = COALESCE(LAST_INSERT_ID(), @nginxUpstreamMenuId);

-- 按钮权限（类型=3：按钮/权限）
INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT '查询Nginx Upstream', 3, 1, 1, 'operations:nginx_upstream:query', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, '查询Nginx Upstream', NULL, 0, @nginxUpstreamMenuId, '查询Nginx Upstream配置', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = '查询Nginx Upstream' AND `permission` = 'operations:nginx_upstream:query');

INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT '创建Nginx Upstream', 3, 2, 1, 'operations:nginx_upstream:create', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, '创建Nginx Upstream', NULL, 0, @nginxUpstreamMenuId, '创建Nginx Upstream配置', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = '创建Nginx Upstream' AND `permission` = 'operations:nginx_upstream:create');

INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT '修改Nginx Upstream', 3, 3, 1, 'operations:nginx_upstream:update', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, '修改Nginx Upstream', NULL, 0, @nginxUpstreamMenuId, '修改Nginx Upstream配置', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = '修改Nginx Upstream' AND `permission` = 'operations:nginx_upstream:update');

INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT '删除Nginx Upstream', 3, 4, 1, 'operations:nginx_upstream:delete', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, '删除Nginx Upstream', NULL, 0, @nginxUpstreamMenuId, '删除Nginx Upstream配置', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = '删除Nginx Upstream' AND `permission` = 'operations:nginx_upstream:delete');

INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT 'Nginx Upstream健康检查', 3, 5, 1, 'operations:nginx_upstream:health_check', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, 'Nginx Upstream健康检查', NULL, 0, @nginxUpstreamMenuId, '执行Nginx Upstream健康检查', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = 'Nginx Upstream健康检查' AND `permission` = 'operations:nginx_upstream:health_check');

INSERT INTO `system_menu` (name, type, `order`, status, permission, icon, route_name, route_path, component_path, redirect, hidden, keep_alive, always_show, title, params, affix, parent_id, description, created_at, updated_at)
SELECT '同步Nginx Upstream配置', 3, 6, 1, 'operations:nginx_upstream:sync', NULL, NULL, NULL, NULL, NULL, 0, 1, 0, '同步Nginx Upstream配置', NULL, 0, @nginxUpstreamMenuId, '同步Nginx Upstream配置到Nginx节点', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM `system_menu` WHERE `name` = '同步Nginx Upstream配置' AND `permission` = 'operations:nginx_upstream:sync');
