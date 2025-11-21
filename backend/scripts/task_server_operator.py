# -*- coding: utf-8 -*-
"""
服务器操作任务执行器（初始化等）
通过任务类型命名，方便调用
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from base_batch_task_executor import BaseBatchTaskExecutor


class ServerOperatorTaskExecutor(BaseBatchTaskExecutor):
    """服务器操作任务执行器（初始化等）"""
    
    def print_init_info(self):
        """打印初始化信息"""
        super().print_init_info()
        
        # 打印节点信息
        total_nodes = 0
        for idx, meta in enumerate(self.operator_metas, 1):
            node_ids = meta.get("node_ids", [])
            nodes = meta.get("nodes", [])
            node_count = len(nodes) if nodes else len(node_ids)
            total_nodes += node_count
            
            self.write_log(f"批次 {idx}: {node_count} 个节点")
            if nodes:
                for node in nodes:
                    node_ip = node.get("ip") if isinstance(node, dict) else getattr(node, "ip", "unknown")
                    node_port = node.get("port") if isinstance(node, dict) else getattr(node, "port", 22)
                    self.write_log(f"  - {node_ip}:{node_port}")
            elif node_ids:
                self.write_log(f"  - 节点IDs: {node_ids}")
        
        self.write_log(f"总节点数: {total_nodes}")
        self.write_log("=" * 60)
    
    def _execute_task(self) -> int:
        """
        执行服务器操作任务逻辑
        根据 operator_type 执行不同的操作（init 等）
        """
        if self.task_type == "init":
            return self._execute_init()
        else:
            self.write_log(f"[ERROR] 不支持的操作类型: {self.task_type}")
            return 1
    
    def _execute_init(self) -> int:
        """
        执行服务器初始化任务逻辑
        """
        self.write_log("开始执行服务器初始化任务")
        self.output_progress(10, "初始化服务器环境")
        
        # TODO: 实现具体的服务器初始化逻辑
        # 这里可以根据 operator_metas 中的参数执行不同的初始化操作
        # 例如：安装基础软件、配置系统参数、创建用户等
        
        for idx, meta in enumerate(self.operator_metas, 1):
            node_ids = meta.get("node_ids", [])
            nodes = meta.get("nodes", [])
            
            self.write_log(f"处理批次 {idx}: {len(nodes) if nodes else len(node_ids)} 个节点")
            self.output_progress(20 + idx * 20, f"处理批次 {idx}")
            
            # 示例：遍历节点执行初始化
            target_nodes = nodes if nodes else [{"id": nid} for nid in node_ids]
            for node in target_nodes:
                node_id = node.get("id") if isinstance(node, dict) else getattr(node, "id", None)
                node_ip = node.get("ip") if isinstance(node, dict) else getattr(node, "ip", "unknown")
                
                self.write_log(f"  初始化节点 {node_id} ({node_ip})")
                # TODO: 执行实际的初始化操作
                # 例如：SSH连接、执行命令等
        
        self.output_progress(100, "服务器初始化完成")
        self.write_log("服务器初始化任务执行完成")
        return 0


def execute_in_process(
    *,
    log_path: Path,
    task_id: int,
    task_type: str,
    operator_metas: List[Dict],
    log_handler: Optional[Callable[[str], None]] = None,
    progress_handler: Optional[Callable[[int, str], None]] = None,
) -> int:
    """
    在当前进程中执行服务器操作任务
    """
    executor = ServerOperatorTaskExecutor(
        log_path=log_path,
        task_id=task_id,
        task_type=task_type,
        operator_metas=operator_metas,
        log_handler=log_handler,
        progress_handler=progress_handler,
    )
    return executor.execute()


if __name__ == "__main__":
    # 从环境变量获取参数
    import os
    import json
    
    task_params_json = os.environ.get("TASK_PARAMS_JSON")
    if task_params_json:
        params = json.loads(task_params_json)
        log_path = Path(params["log_path"])
        task_id = params["task_id"]
        task_type = params["task_type"]
        operator_metas = params["operator_metas"]
    else:
        log_path = Path(os.environ.get("BATCH_LOG_PATH", ""))
        task_id = int(os.environ.get("BATCH_TASK_ID", "0"))
        task_type = os.environ.get("BATCH_TASK_TYPE", "")
        operator_metas = json.loads(os.environ.get("BATCH_OPERATOR_METAS", "[]"))
    
    exit_code = execute_in_process(
        log_path=log_path,
        task_id=task_id,
        task_type=task_type,
        operator_metas=operator_metas,
    )
    sys.exit(exit_code)

