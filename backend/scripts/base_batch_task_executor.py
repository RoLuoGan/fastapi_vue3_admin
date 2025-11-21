# -*- coding: utf-8 -*-
"""
批次任务执行器基类
所有任务执行器都应该继承此类
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable


class BaseBatchTaskExecutor(ABC):
    """批次任务执行器基类"""
    
    def __init__(
        self,
        log_path: Path,
        task_id: int,
        task_type: str,
        operator_metas: List[Dict],
        log_handler: Optional[Callable[[str], None]] = None,
        progress_handler: Optional[Callable[[int, str], None]] = None,
    ):
        """
        初始化执行器
        
        Args:
            log_path: 日志文件路径
            task_id: 任务ID
            task_type: 任务类型 (deploy/restart/init 等)
            operator_metas: 操作元数据列表（任意结构）
            log_handler: 日志处理回调
            progress_handler: 进度处理回调
        """
        self.log_path = log_path
        self.task_id = task_id
        self.task_type = task_type
        self.operator_metas = operator_metas
        self.start_time = datetime.now()
        self.log_handler = log_handler
        self.progress_handler = progress_handler
        
    def write_log(self, message: str):
        """
        输出日志到标准输出（由 executor 统一写入日志文件）
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        
        if self.log_handler:
            self.log_handler(log_line)
            return
        
        try:
            print(log_line, flush=True)
        except (UnicodeEncodeError, OSError):
            safe_line = log_line.encode('ascii', errors='replace').decode('ascii')
            print(safe_line, flush=True)
    
    def output_progress(self, progress: int, message: str):
        """
        输出进度信息（特殊格式，用于进度解析）
        
        Args:
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        if self.progress_handler:
            self.progress_handler(progress, message)
        
        progress_line = f"PROGRESS: {progress} - {message}"
        self.write_log(progress_line)
    
    def print_init_info(self):
        """打印初始化信息（子类可以重写以自定义输出）"""
        self.write_log("=" * 60)
        self.write_log(f"批次任务执行器初始化")
        self.write_log(f"任务ID: {self.task_id}")
        self.write_log(f"任务类型: {self.task_type}")
        self.write_log(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.write_log(f"日志路径: {self.log_path}")
        self.write_log(f"元数据数量: {len(self.operator_metas)}")
        self.write_log("=" * 60)
    
    def execute(self) -> int:
        """
        执行批次任务（主入口方法）
        
        返回:
            int: 退出码，0 表示成功，非0 表示失败
        """
        try:
            # 打印初始化信息
            self.print_init_info()
            
            # 调用具体的执行逻辑（由子类实现）
            return self._execute_task()
            
        except KeyboardInterrupt:
            self.write_log("[ERROR] 任务被用户中断")
            self.output_progress(100, "任务被中断")
            return 130  # SIGINT 退出码
        except Exception as exc:
            error_msg = f"[ERROR] 任务执行异常: {exc}"
            self.write_log(error_msg)
            import traceback
            self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
            self.output_progress(100, f"任务异常: {exc}")
            return 1
    
    @abstractmethod
    def _execute_task(self) -> int:
        """
        执行具体任务逻辑（由子类实现）
        
        返回:
            int: 退出码，0 表示成功，非0 表示失败
        """
        pass

