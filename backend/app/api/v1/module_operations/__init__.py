# -*- coding: utf-8 -*-

from fastapi import APIRouter

from .service_module import ServiceRouter
from .service_package import ServicePackageRouter
from .server import ServerRouter
from .task import TaskRouter
from .prometheus import PrometheusRouter
from .nginx_upstream import router as NginxUpstreamRouter
from .celery_worker import CeleryWorkerRouter
from .script import ScriptRouter
from .aiagent import AIAgentRouter


OperationsRouter = APIRouter(prefix="/operations")
OperationsRouter.include_router(ServiceRouter)
OperationsRouter.include_router(ServicePackageRouter)
OperationsRouter.include_router(ServerRouter)
OperationsRouter.include_router(TaskRouter)
OperationsRouter.include_router(PrometheusRouter)
OperationsRouter.include_router(NginxUpstreamRouter)
OperationsRouter.include_router(CeleryWorkerRouter)
OperationsRouter.include_router(ScriptRouter)
OperationsRouter.include_router(AIAgentRouter)

