# -*- coding: utf-8 -*-
"""
节点操作任务执行器（部署/重启）
通过任务类型命名，方便调用
"""

import json
import os
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from base_batch_task_executor import BaseBatchTaskExecutor

class NodeOperatorTaskExecutor(BaseBatchTaskExecutor):
    """节点操作任务执行器（部署/重启）"""
    
    def print_init_info(self):
        """打印初始化信息"""
        super().print_init_info()
        
        # 打印模块和节点信息
        if not self.operator_metas:
            self.write_log("[WARNING] operator_metas 为空")
            self.write_log("=" * 60)
            return
        
        self.write_log(f"模块数量: {len(self.operator_metas)}")
        total_nodes = 0
        
        for idx, meta in enumerate(self.operator_metas, 1):
            if not isinstance(meta, dict):
                self.write_log(f"[WARNING] 模块 {idx} 不是字典类型: {type(meta)}")
                continue
                
            service_id = meta.get("service_id")
            service_name = meta.get("service_name", f"服务ID:{service_id}")
            nodes = meta.get("nodes", [])
            
            # 兼容性处理：如果 nodes 为空但 node_ids 存在，尝试打印警告
            if not nodes and meta.get("node_ids"):
                self.write_log(f"[WARNING] 模块 {service_name} (ID:{service_id}) 缺少节点详情 (nodes)，仅有 IDs: {meta.get('node_ids')}")
                self.write_log(f"[DEBUG] Meta keys: {list(meta.keys())}")
            
            node_count = len(nodes)
            total_nodes += node_count
            
            self.write_log(f"模块 {idx}: {service_name} (ID:{service_id}) - {node_count} 个节点")
            for node_idx, node in enumerate(nodes, 1):
                if isinstance(node, dict):
                    node_ip = node.get("ip", "unknown")
                    node_port = node.get("port", 22)
                else:
                    node_ip = getattr(node, "ip", "unknown")
                    node_port = getattr(node, "port", 22)
                self.write_log(f"  - [{node_idx}/{node_count}] {node_ip}:{node_port}")
        
        self.write_log(f"总节点数: {total_nodes}")
        self.write_log("=" * 60)
    
    def _execute_task(self) -> int:
        """
        根据任务类型执行节点操作逻辑。
        """
        try:
            if self.task_type == "deploy":
                return self._execute_deploy()
            if self.task_type == "restart":
                return self._execute_restart()
            if self.task_type == "start":
                return self._execute_start()
            if self.task_type == "stop":
                return self._execute_stop()
            
            self.write_log(f"[ERROR] 未知任务类型: {self.task_type}")
            return 1
        except Exception as exc:
            self.write_log(f"[ERROR] 执行 {self.task_type} 任务失败: {exc}")
            import traceback
            self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
            return 1

    # ------------------------------------------------------------------
    # 新部署逻辑
    # ------------------------------------------------------------------
    def _execute_deploy(self) -> int:
        """
        从 OSS 下载版本包并通过 Ansible Playbook 分发与执行。
        根据 service_type 分组执行不同的 playbook。
        """
        back_date = datetime.now().strftime("%m%d")
        
        # 1. 准备阶段：按模块类型 (service_type) 分组任务
        # 结构: { "java": [meta1, meta2], "nginx": [meta3], "default": [meta4] }
        grouped_metas: Dict[str, List[Dict[str, Any]]] = {}
        
        # 预处理并下载文件
        for meta in self.operator_metas:
            package_key = meta.get("package_path")
            if not package_key:
                self.write_log(f"[WARNING] 模块 {meta.get('service_name')} 缺少 package_path，跳过")
                continue
            
            try:
                local_pkg = self.download_oss_object(package_key)
                remote_path = meta.get("remote_path") or f"/data/service/{meta.get('service_name')}"
                restart_command = meta.get("restart_command") or f"supervisorctl restart {meta.get('service_name')}"
                
                # 获取模块类型，默认为 'default'
                # 优先从 meta 中获取，也可以尝试根据 service_name 或其他字段推断
                service_type = meta.get("module_group") or "default"
                # 将 module_group 映射到 playbook 名称后缀
                # 假设 module_group 值为 'java', 'nginx' 等。如果是中文或其他，需要映射
                # 简单的归一化处理，实际可能需要查表
                service_type_key = service_type.lower() if service_type else "default"
                if "java" in service_type_key:
                    service_type_key = "java"
                elif "nginx" in service_type_key:
                    service_type_key = "nginx"
                else:
                    # 报错
                    raise ValueError(f"服务：{meta.get('service_name')} 模块分组：{service_type}, 请检查 module_group 字段")
                
                # 构造带 ansbile_vars 的 meta 副本
                new_meta = meta.copy()
                new_meta["ansible_vars"] = {
                    "service_name": meta.get("service_name"),
                    "local_pkg_path": str(local_pkg),
                    "remote_pkg_path": remote_path,
                    "restart_command": restart_command,
                    "back_date": back_date,
                }
                
                if service_type_key not in grouped_metas:
                    grouped_metas[service_type_key] = []
                grouped_metas[service_type_key].append(new_meta)
                
            except Exception as e:
                self.write_log(f"[ERROR] 准备模块 {meta.get('service_name')} 失败: {e}")
                raise e

        if not grouped_metas:
            self.write_log("[ERROR] 没有有效的部署任务可执行")
            return 1

        # 2. 分组执行 Playbook
        final_rc = 0
        for service_type, metas in grouped_metas.items():
            # 确定 playbook 路径
            # 命名规范: deploy_{service_type}.yml (e.g., deploy_java.yml, deploy_nginx.yml)
            playbook_name = f"deploy_{service_type}.yml"
            playbook_path = Path(__file__).parent / "ansible_playbooks" / playbook_name
            
            # 如果特定类型的 playbook 不存在，回退到 deploy_default.yml 或 deploy.yml
            if not playbook_path.exists():
                self.write_log(f"[WARNING] Playbook {playbook_name} 不存在，尝试使用 deploy_default.yml")
                playbook_path = Path(__file__).parent / "ansible_playbooks" / "deploy_default.yml"
                if not playbook_path.exists():
                     self.write_log(f"[WARNING] deploy_default.yml 也不存在，尝试使用 deploy.yml")
                     playbook_path = Path(__file__).parent / "ansible_playbooks" / "deploy.yml"

            self.write_log(f"准备执行分组部署: 类型={service_type}, 模块数={len(metas)}, Playbook={playbook_path.name}")
            
            # 生成该组的 Inventory
            inventory_path = self.generate_ansible_inventory(metas)
            
            # 执行 Playbook
            self.write_log(f"执行 Playbook: {playbook_path} -> Hosts: all")
            
            rc = self.run_ansible_playbook(
                playbook=playbook_path,
                inventory=inventory_path,
                extra_vars={"target_hosts": "all"}
            )
            
            if rc != 0:
                final_rc = rc
                self.write_log(f"[ERROR] 分组 {service_type} 部署失败，返回码: {rc}")
            else:
                self.write_log(f"[SUCCESS] 分组 {service_type} 部署成功")
        
        return final_rc
    
    def _execute_restart(self) -> int:
        """重启"""
        return self._execute_service_command(action="restart")

    def _execute_start(self) -> int:
        """启动"""
        return self._execute_service_command(action="start")

    def _execute_stop(self) -> int:
        """停止"""
        return self._execute_service_command(action="stop")

    def _execute_service_command(self, action: str) -> int:
        """
        通过 Ansible Playbook 执行服务控制指令（restart/start/stop）。
        """
        playbook_path = Path(__file__).parent / "ansible_playbooks" / f"{action}.yml"
        inventory_metas: List[Dict[str, Any]] = []

        for meta in self.operator_metas:
            service_name = meta.get("service_name")
            restart_command = "supervisorctl restart {service_name}" if action == "restart" else None
            start_command = "supervisorctl start {service_name}" if action == "start" else None
            stop_command = "supervisorctl stop {service_name}" if action == "stop" else None

            new_meta = meta.copy()
            new_meta["ansible_vars"] = {
                "service_name": service_name,
                "restart_command": restart_command,
                "start_command": start_command,
                "stop_command": stop_command,
            }
            inventory_metas.append(new_meta)

        if not inventory_metas:
            self.write_log(f"[ERROR] 没有有效的 {action} 任务可执行")
            return 1

        inventory_path = self.generate_ansible_inventory(inventory_metas)
        self.write_log(f"批量执行{action} Playbook: {playbook_path} -> Hosts: all")

        # restart 之前保留的延时逻辑，复用到所有操作，避免瞬时触发
        time.sleep(2 if action in {"start", "stop"} else 10)

        rc = self.run_ansible_playbook(
            playbook=playbook_path,
            inventory=inventory_path,
            extra_vars={"target_hosts": "all"}
        )

        return 0 if rc == 0 else 1
    
    def _resolve_group_name(self, meta: Dict[str, Any]) -> str:
        name = meta.get("service_name") or f"service_{meta.get('service_id')}"
        return name.replace(" ", "_")


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

