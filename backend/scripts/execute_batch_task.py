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
from typing import Dict, Any, Optional, List, Callable
import subprocess
import threading

EXTENSION_NAME = "demo_task_script.py"

class BatchTaskExecutor:
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
            task_type: 任务类型 (deploy/restart)
            operator_metas: 操作元数据列表
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
        执行具体任务逻辑：调用外部脚本，由脚本自身处理节点与业务逻辑
        """
        extension_script = Path(__file__).with_name(EXTENSION_NAME)
        if not extension_script.exists():
            raise FileNotFoundError(f"未找到示例脚本: {extension_script}")
        
        self.write_log(f"开始执行外部脚本 {extension_script}")
        self.output_progress(5, "初始化外部脚本")
        
        env_override = {
            "BATCH_TASK_ID": str(self.task_id),
            "BATCH_TASK_TYPE": self.task_type,
            "BATCH_LOG_PATH": str(self.log_path),
            "BATCH_OPERATOR_METAS": json.dumps(self.operator_metas, ensure_ascii=False),
        }
        
        return_code = self._run_external_script(extension_script, env_override=env_override)

        if return_code == 0:
            self.output_progress(100, "外部脚本执行完成")
            self.write_log("外部脚本执行结束，返回码 0")
        else:
            self.output_progress(100, f"外部脚本执行失败 ({return_code})")
            self.write_log(f"[ERROR] 外部脚本执行失败，退出码: {return_code}")
        
        return return_code

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
        
        return process.wait()


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
    在当前进程中执行批次任务
    """
    executor = BatchTaskExecutor(
        log_path=log_path,
        task_id=task_id,
        task_type=task_type,
        operator_metas=operator_metas,
        log_handler=log_handler,
        progress_handler=progress_handler,
    )
    return executor.execute()


def execute_in_subprocess(
    *,
    log_path: Path,
    task_id: int,
    task_type: str,
    operator_metas: List[Dict],
    python_executable: Optional[str] = None,
    base_dir: Optional[Path] = None,
    extra_env: Optional[Dict[str, str]] = None,
    log_handler: Optional[Callable[[str, str], None]] = None,
) -> int:
    """
    通过 subprocess 执行脚本，并实时读取日志
    
    Args:
        log_path: 日志文件路径
        task_id: 任务ID
        task_type: 任务类型
        operator_metas: 操作元数据
        python_executable: 指定 Python 解释器
        base_dir: 工作目录
        extra_env: 额外环境变量
        log_handler: 日志回调 (source, line)
    """
    script_path = Path(__file__).resolve()
    if python_executable is None:
        python_executable = sys.executable
    
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    
    params_dict = {
        "log_path": str(log_path),
        "task_id": task_id,
        "task_type": task_type,
        "operator_metas": operator_metas,
    }
    env["TASK_PARAMS_JSON"] = json.dumps(params_dict, ensure_ascii=False)
    
    cmd = [python_executable, str(script_path)]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(base_dir or script_path.parent),
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        text=True,
    )
    
    def _handle_output(stream, source):
        for raw_line in iter(stream.readline, ''):
            line = raw_line.rstrip('\r\n')
            if not line:
                continue
            if log_handler:
                log_handler(source, line)
            else:
                print(f"[{source}] {line}")
    
    threads = [
        threading.Thread(target=_handle_output, args=(process.stdout, "stdout"), daemon=True),
        threading.Thread(target=_handle_output, args=(process.stderr, "stderr"), daemon=True),
    ]
    
    for thread in threads:
        thread.start()
    
    return_code = process.wait()
    
    for thread in threads:
        thread.join(timeout=1)
    
    return return_code




