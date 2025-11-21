# -*- coding: utf-8 -*-
"""
节点操作任务执行器（部署/重启）
通过任务类型命名，方便调用
"""

import sys
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from base_batch_task_executor import BaseBatchTaskExecutor

EXTENSION_NAME = "demo_task_script.py"


class NodeOperatorTaskExecutor(BaseBatchTaskExecutor):
    """节点操作任务执行器（部署/重启）"""
    
    def print_init_info(self):
        """打印初始化信息"""
        super().print_init_info()
        
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
                node_ip = node.get("ip") if isinstance(node, dict) else getattr(node, "ip", "unknown")
                node_port = node.get("port") if isinstance(node, dict) else getattr(node, "port", 22)
                self.write_log(f"  - {node_ip}:{node_port}")
        
        self.write_log(f"总节点数: {total_nodes}")
        self.write_log("=" * 60)
    
    def _execute_task(self) -> int:
        """
        执行具体任务逻辑：调用外部脚本，由脚本自身处理节点与业务逻辑
        """
        extension_script = Path(__file__).parent / EXTENSION_NAME
        if not extension_script.exists():
            raise FileNotFoundError(f"未找到示例脚本: {extension_script}")
        
        self.write_log(f"开始执行外部脚本 {extension_script}")
        self.output_progress(5, "初始化外部脚本")
        
        env_override = {
            "BATCH_TASK_ID": str(self.task_id),
            "BATCH_TASK_TYPE": self.task_type,
            "BATCH_LOG_PATH": str(self.log_path),
            "BATCH_OPERATOR_METAS": json.dumps(self.operator_metas, ensure_ascii=False, default=str),
        }
        
        return self._run_external_script(extension_script, env_override=env_override)

    def _run_external_script(
        self,
        script_path: Path,
        *,
        env_override: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        调用外部脚本并将输出写入日志
        """
        cmd = [sys.executable, str(script_path)]
        env = os.environ.copy()
        if env_override:
            env.update({k: str(v) for k, v in env_override.items() if v is not None})
        
        self.write_log(f"调用外部脚本: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            text=True,
        )
        
        if process.stdout:
            for raw_line in iter(process.stdout.readline, ''):
                line = raw_line.rstrip('\r\n')
                if line:
                    self.write_log(f"[脚本输出] {line}")
            process.stdout.close()
        
        return_code = process.wait()

        if return_code == 0:
            self.output_progress(100, "外部脚本执行完成")
            self.write_log("外部脚本执行结束，返回码 0")
        else:
            self.output_progress(100, f"外部脚本执行失败 ({return_code})")
            self.write_log(f"[ERROR] 外部脚本执行失败，退出码: {return_code}")
        
        return return_code


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
    在当前进程中执行节点操作任务
    """
    executor = NodeOperatorTaskExecutor(
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

