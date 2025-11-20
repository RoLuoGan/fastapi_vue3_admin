# -*- coding: utf-8 -*-
"""
任务日志 CRUD
"""

from typing import Dict, List, Optional, Sequence, Union, Any
from sqlalchemy import select, func
from sqlalchemy.engine import Result

from app.core.base_crud import CRUDBase
from app.core.exceptions import CustomException
from app.api.v1.module_system.auth.schema import AuthSchema

from ..models import TaskLogModel


class TaskLogCRUD(CRUDBase[TaskLogModel, Dict, Dict]):
    """任务日志数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=TaskLogModel, auth=auth)

    async def get_max_seq_crud(self, task_id: int) -> int:
        """
        获取任务的最大 seq
        
        Args:
            task_id: 任务ID
            
        Returns:
            最大 seq，如果没有日志则返回 0
        """
        try:
            sql = select(func.max(self.model.seq)).where(self.model.task_id == task_id)
            result: Result = await self.db.execute(sql)
            max_seq = result.scalar()
            return max_seq if max_seq is not None else 0
        except Exception as exc:
            raise CustomException(msg=f"获取最大 seq 失败: {str(exc)}")

    async def add_log_crud(
        self,
        task_id: int,
        seq: int,
        content: str,
        line_count: int = 1,
        timestamp: Optional[int] = None,
    ) -> TaskLogModel:
        """
        添加日志记录
        
        Args:
            task_id: 任务ID
            seq: 全局序号
            content: 日志内容
            line_count: 行数
            timestamp: Unix时间戳（秒）
            
        Returns:
            创建的日志记录
        """
        try:
            data = {
                "task_id": task_id,
                "seq": seq,
                "content": content,
                "line_count": line_count,
                "timestamp": timestamp,
            }
            return await self.create(data=data)
        except Exception as exc:
            raise CustomException(msg=f"添加日志失败: {str(exc)}")

    async def get_logs_by_seq_range_crud(
        self,
        task_id: int,
        start_seq: int,
        end_seq: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Sequence[TaskLogModel]:
        """
        根据 seq 范围获取日志
        
        Args:
            task_id: 任务ID
            start_seq: 起始 seq（包含）
            end_seq: 结束 seq（包含），如果为 None 则只限制 start_seq
            limit: 限制数量
            
        Returns:
            日志记录列表，按 seq 升序排列
        """
        try:
            sql = select(self.model).where(
                self.model.task_id == task_id,
                self.model.seq >= start_seq,
            )
            
            if end_seq is not None:
                sql = sql.where(self.model.seq <= end_seq)
            
            sql = sql.order_by(self.model.seq.asc())
            
            if limit is not None:
                sql = sql.limit(limit)
            
            sql = await self._CRUDBase__filter_permissions(sql)
            result: Result = await self.db.execute(sql)
            return result.scalars().all()
        except Exception as exc:
            raise CustomException(msg=f"获取日志失败: {str(exc)}")

    async def get_logs_after_seq_crud(
        self,
        task_id: int,
        last_seq: int,
        limit: Optional[int] = None,
    ) -> Sequence[TaskLogModel]:
        """
        获取 last_seq 之后的日志（用于断点续传）
        
        Args:
            task_id: 任务ID
            last_seq: 最后读取的 seq，返回大于该 seq 的日志
            limit: 限制数量
            
        Returns:
            日志记录列表，按 seq 升序排列
        """
        return await self.get_logs_by_seq_range_crud(
            task_id=task_id,
            start_seq=last_seq + 1,
            limit=limit,
        )

    async def delete_logs_by_task_id_crud(self, task_id: int) -> None:
        """
        删除任务的所有日志
        
        Args:
            task_id: 任务ID
        """
        try:
            await self.delete_by_field(field="task_id", value=task_id)
        except Exception as exc:
            raise CustomException(msg=f"删除任务日志失败: {str(exc)}")

