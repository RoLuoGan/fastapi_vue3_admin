-- 添加服务节点启动和停止的菜单权限
-- 注意：这里只添加菜单数据，不涉及表结构变更
-- 假设 OperationsNode 菜单的 ID 需要查询获得，这里用 SQL 变量处理

-- 1. 获取"服务节点管理"菜单的 ID
SET @parent_id = (SELECT id FROM system_menus WHERE route_name = 'OperationsNode' LIMIT 1);

-- 2. 获取当前最大的菜单 ID (可选，如果不自增或需要手动指定顺序)
-- SET @max_id = (SELECT MAX(id) FROM system_menus);

-- 3. 插入"启动服务"菜单/权限
INSERT INTO system_menus (
    parent_id,
    menu_type,
    name,
    title,
    path,
    component,
    perms,
    icon,
    sort,
    status,
    show_status,
    created_at,
    updated_at
)
SELECT 
    @parent_id,
    3, -- 按钮/权限
    '启动服务',
    '启动服务',
    NULL,
    NULL,
    'operations:node:start',
    NULL,
    7, -- 排序，接在重启服务后面
    1, -- 启用
    1, -- 显示
    NOW(),
    NOW()
WHERE @parent_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM system_menus WHERE perms = 'operations:node:start');

-- 4. 插入"停止服务"菜单/权限
INSERT INTO system_menus (
    parent_id,
    menu_type,
    name,
    title,
    path,
    component,
    perms,
    icon,
    sort,
    status,
    show_status,
    created_at,
    updated_at
)
SELECT 
    @parent_id,
    3, -- 按钮/权限
    '停止服务',
    '停止服务',
    NULL,
    NULL,
    'operations:node:stop',
    NULL,
    8, -- 排序
    1, -- 启用
    1, -- 显示
    NOW(),
    NOW()
WHERE @parent_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM system_menus WHERE perms = 'operations:node:stop');

