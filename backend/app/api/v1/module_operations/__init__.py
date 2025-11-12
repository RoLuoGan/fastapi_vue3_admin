# -*- coding: utf-8 -*-

from fastapi import APIRouter

from .service_module import ServiceRouter
from .server import ServerRouter
from .task import TaskRouter


OperationsRouter = APIRouter(prefix="/operations")
OperationsRouter.include_router(ServiceRouter)
OperationsRouter.include_router(ServerRouter)
OperationsRouter.include_router(TaskRouter)

