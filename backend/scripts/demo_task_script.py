# -*- coding: utf-8 -*-
"""
示例任务脚本：仅打印日志，模拟节点执行过程。
可根据实际需求替换为真实的部署/运维脚本。
"""

import os
import json
import time
import sys
import io
from datetime import datetime
from typing import List, Dict, Any


# 兼容windows编码
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


def log(message: str) -> None:
    """标准化日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def progress(progress: int, message: str) -> None:
    """标准化进度输出"""
    print(f"PROGRESS: {progress} - {message}", flush=True)

def load_params() -> Dict[str, Any]:
    """从环境变量读取批次任务参数"""
    params = {
        "task_id": os.getenv("BATCH_TASK_ID"),
        "task_type": os.getenv("BATCH_TASK_TYPE"),
        "log_path": os.getenv("BATCH_LOG_PATH"),
    }
    operator_metas_raw = os.getenv("BATCH_OPERATOR_METAS", "[]")
    try:
        params["operator_metas"] = json.loads(operator_metas_raw)
    except json.JSONDecodeError:
        params["operator_metas"] = []
    return params


def run_demo(operator_metas: List[Dict[str, Any]]) -> None:
    """执行 demo 步骤，仅打印日志"""
    steps = [
        "准备运行环境",
        "执行核心逻辑",
        "清理现场并收尾",
    ]
    
    total_nodes = sum(len(meta.get("nodes", [])) for meta in operator_metas) or 1
    processed_nodes = 0
    
    for meta_idx, meta in enumerate(operator_metas, 1):
        service_name = meta.get("service_name") or f"服务ID:{meta.get('service_id')}"
        nodes = meta.get("nodes", [])
        log(f"模块 {meta_idx}/{len(operator_metas)} -> {service_name}, 节点数: {len(nodes)}")
        
        for node in nodes:
            node_ip = node.get("ip", "unknown")
            node_port = node.get("port", 22)
            log(f"  - 节点 {node_ip}:{node_port} 开始 Demo 流程")
            
            for idx, step in enumerate(steps, 1):
                log(f"    步骤 {idx}/{len(steps)}: {step}")
                time.sleep(0.2)
            
            log(f"  - 节点 {node_ip}:{node_port} Demo 流程完成")
            processed_nodes += 1
            progress(processed_nodes / total_nodes * 100, f"{service_name}::{node_ip}")
        
        if not nodes:
            log("  - 未配置节点，跳过")
    
    log("Demo 脚本执行完成，所有节点处理结束")


def main():
    params = load_params()
    log(f"Demo 脚本启动 -> TaskID: {params.get('task_id')} Type: {params.get('task_type')}")
    log(f"日志文件: {params.get('log_path')}")
    run_demo(params.get("operator_metas", []))


if __name__ == "__main__":
    main()

