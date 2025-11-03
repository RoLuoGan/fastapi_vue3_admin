# -*- coding: utf-8 -*-

from fastapi import APIRouter

from .node.controller import NodeRouter


OperationsRouter = APIRouter(prefix="/operations")

# 包含所有子路由
OperationsRouter.include_router(NodeRouter)

