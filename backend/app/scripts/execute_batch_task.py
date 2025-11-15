# -*- coding: utf-8 -*-
"""
批次任务执行脚本
通过 subprocess 调用，实时输出日志，支持进度更新

所有参数均从环境变量获取：
- TASK_LOG_PATH: 日志文件路径
- TASK_ID: 任务ID
- TASK_TYPE: 任务类型 (deploy/restart)
- OPERATOR_METAS: 操作元数据（JSON字符串）
或者使用 TASK_PARAMS_JSON 传递完整参数（JSON字符串，包含所有参数）
"""

import sys
import os
import json
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Windows 编码兼容处理
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace', 
                line_buffering=True
            )
    except (AttributeError, OSError):
        pass
    
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, 
                encoding='utf-8', 
                errors='replace', 
                line_buffering=True
            )
    except (AttributeError, OSError):
        pass


class BatchTaskExecutor:
    """批次任务执行器基类"""
    
    def __init__(self, log_path: Path, task_id: int, task_type: str, operator_metas: List[Dict]):
        """
        初始化执行器
        
        Args:
            log_path: 日志文件路径
            task_id: 任务ID
            task_type: 任务类型 (deploy/restart)
            operator_metas: 操作元数据列表
        """
        self.log_path = log_path
        self.task_id = task_id
        self.task_type = task_type
        self.operator_metas = operator_metas
        self.start_time = datetime.now()
        
    def write_log(self, message: str):
        """
        输出日志到标准输出（由 executor 统一写入日志文件）
        
        Args:
            message: 日志消息
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        
        # 只输出到标准输出（由 executor 统一写入日志文件，避免重复）
        try:
            print(log_line, flush=True)
        except (UnicodeEncodeError, OSError):
            # 如果输出失败，尝试 ASCII 安全版本
            safe_line = log_line.encode('ascii', errors='replace').decode('ascii')
            print(safe_line, flush=True)
    
    def output_progress(self, progress: int, message: str):
        """
        输出进度信息（特殊格式，用于进度解析）
        
        Args:
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        progress_line = f"PROGRESS: {progress} - {message}"
        self.write_log(progress_line)
    
    def print_init_info(self):
        """打印初始化信息"""
        self.write_log("=" * 60)
        self.write_log(f"批次任务执行器初始化")
        self.write_log(f"任务ID: {self.task_id}")
        self.write_log(f"任务类型: {self.task_type}")
        self.write_log(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.write_log(f"日志路径: {self.log_path}")
        self.write_log(f"模块数量: {len(self.operator_metas)}")
        
        # 打印模块和节点信息
        total_nodes = 0
        for idx, meta in enumerate(self.operator_metas, 1):
            service_id = meta.get("service_id")
            service_name = meta.get("service_name", f"服务ID:{service_id}")
            nodes = meta.get("nodes", [])
            node_count = len(nodes)
            total_nodes += node_count
            
            self.write_log(f"模块 {idx}: {service_name} (ID:{service_id}) - {node_count} 个节点")
            for node in nodes:
                node_ip = node.get("ip", "unknown")
                node_port = node.get("port", 22)
                self.write_log(f"  - {node_ip}:{node_port}")
        
        self.write_log(f"总节点数: {total_nodes}")
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
            
            # 调用具体的执行逻辑（由子类或外部实现）
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
    
    def _execute_task(self) -> int:
        """
        执行具体任务逻辑（需要实现）
        
        返回:
            int: 退出码，0 表示成功，非0 表示失败
        """
        # TODO: 在这里实现具体的任务执行逻辑
        # 示例：
        # self.write_log("开始执行任务...")
        # self.output_progress(10, "任务开始")
        # 
        # for idx, meta in enumerate(self.operator_metas, 1):
        #     service_id = meta.get("service_id")
        #     nodes = meta.get("nodes", [])
        #     # 处理每个模块的节点
        #     for node in nodes:
        #         # 执行节点任务
        #         pass
        # 
        # self.output_progress(100, "任务完成")
        # return 0
        
        raise NotImplementedError("请在 _execute_task 方法中实现具体的任务执行逻辑")


# 注意：此脚本所有参数均从环境变量获取，不再使用命令行参数
# 必需的环境变量：
# - TASK_LOG_PATH: 日志文件路径
# - TASK_ID: 任务ID
# - TASK_TYPE: 任务类型 (deploy/restart)
# - OPERATOR_METAS: 操作元数据（JSON字符串）
# 或者使用 TASK_PARAMS_JSON 传递完整参数（JSON字符串，包含所有参数）


def load_from_env() -> Dict[str, Any]:
    """
    从环境变量加载参数
    
    返回:
        Dict: 参数字典
    """
    params = {}
    
    if "TASK_LOG_PATH" in os.environ:
        params["log_path"] = os.environ["TASK_LOG_PATH"]
    
    if "TASK_ID" in os.environ:
        try:
            params["task_id"] = int(os.environ["TASK_ID"])
        except ValueError:
            pass
    
    if "TASK_TYPE" in os.environ:
        params["task_type"] = os.environ["TASK_TYPE"]
    
    if "OPERATOR_METAS" in os.environ:
        try:
            params["operator_metas"] = json.loads(os.environ["OPERATOR_METAS"])
        except (json.JSONDecodeError, TypeError):
            pass
    
    if "TASK_PARAMS_JSON" in os.environ:
        try:
            full_params = json.loads(os.environ["TASK_PARAMS_JSON"])
            params.update(full_params)
        except (json.JSONDecodeError, TypeError):
            pass
    
    return params


def main():
    """主函数 - 所有参数从环境变量获取"""
    # 从环境变量加载所有参数
    params = load_from_env()
    
    # 提取参数
    log_path_str = params.get("log_path")
    task_id = params.get("task_id")
    task_type = params.get("task_type")
    operator_metas = params.get("operator_metas")
    
    # 验证必需参数
    if not log_path_str:
        print("[ERROR] 缺少必需环境变量: TASK_LOG_PATH", file=sys.stderr)
        sys.exit(1)
    
    if task_id is None:
        print("[ERROR] 缺少必需环境变量: TASK_ID", file=sys.stderr)
        sys.exit(1)
    
    if not task_type:
        print("[ERROR] 缺少必需环境变量: TASK_TYPE", file=sys.stderr)
        sys.exit(1)
    
    if not operator_metas:
        print("[ERROR] 缺少必需环境变量: OPERATOR_METAS 或 TASK_PARAMS_JSON", file=sys.stderr)
        sys.exit(1)
    
    # 创建执行器
    log_path = Path(log_path_str)
    executor = BatchTaskExecutor(
        log_path=log_path,
        task_id=task_id,
        task_type=task_type,
        operator_metas=operator_metas
    )
    
    # 执行任务
    exit_code = executor.execute()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

