# -*- coding: utf-8 -*-

from fastapi import APIRouter

# 系统管理模块
from .module_system import SystemRouter

# 监控管理模块
from .module_monitor import MonitorRouter

# 通用模块
from .module_common import CommonRouter

# 应用模块
from .module_application import ApplicationRouter

# 代码生成模块
from .module_generator import GeneratorRouter

# 运维管理模块
from .module_operations import OperationsRouter


# 创建主路由
router = APIRouter()

# 注册各模块路由
router.include_router(SystemRouter)
router.include_router(MonitorRouter)
router.include_router(CommonRouter)
router.include_router(ApplicationRouter)
router.include_router(GeneratorRouter)
router.include_router(OperationsRouter)