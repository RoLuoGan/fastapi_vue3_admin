# -*- coding: utf-8 -*-

from fastapi import APIRouter

from .service_module import ServiceRouter
from .service_package import ServicePackageRouter
from .server import ServerRouter
from .task import TaskRouter
from .prometheus import PrometheusRouter


OperationsRouter = APIRouter(prefix="/operations")
OperationsRouter.include_router(ServiceRouter)
OperationsRouter.include_router(ServicePackageRouter)
OperationsRouter.include_router(ServerRouter)
OperationsRouter.include_router(TaskRouter)
OperationsRouter.include_router(PrometheusRouter)

