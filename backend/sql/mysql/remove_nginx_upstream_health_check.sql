-- 删除 Nginx Upstream 表中的健康检查相关字段
-- 包括：health_check_enabled、health_status、last_check_time

-- 删除健康检查相关字段
ALTER TABLE `operations_nginx_upstream` 
DROP COLUMN IF EXISTS `health_check_enabled`,
DROP COLUMN IF EXISTS `health_status`,
DROP COLUMN IF EXISTS `last_check_time`;

-- 删除健康检查相关菜单权限
DELETE FROM `system_menu` 
WHERE `permission` = 'operations:nginx_upstream:health_check' 
  AND `name` = 'Nginx Upstream健康检查';
