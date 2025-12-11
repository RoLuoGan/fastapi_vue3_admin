# -*- coding: utf-8 -*-
"""
Nginx Upstream 同步任务执行器
通过任务类型命名，方便调用
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from base_batch_task_executor import BaseBatchTaskExecutor


class NginxUpstreamSyncTaskExecutor(BaseBatchTaskExecutor):
    """Nginx Upstream 同步任务执行器"""
    
    def print_init_info(self):
        """打印初始化信息"""
        super().print_init_info()
        
        # 打印upstream和节点信息
        if not self.operator_metas:
            self.write_log("[WARNING] operator_metas 为空")
            self.write_log("=" * 60)
            return
        
        # 统计upstream和节点信息（支持nginx_node_ips数组格式）
        self.write_log(f"Upstream数量: {len(self.operator_metas)}")
        total_nodes = 0
        
        for meta in self.operator_metas:
            if not isinstance(meta, dict):
                self.write_log(f"[WARNING] meta 不是字典类型: {type(meta)}")
                continue
            
            upstream_id = meta.get("upstream_id")
            upstream_name = meta.get("upstream_name", "unknown")
            
            # 支持新的nginx_node_ips数组格式
            nginx_node_ips = meta.get("nginx_node_ips", [])
            if nginx_node_ips:
                # 新格式：nginx_node_ips数组
                node_count = len(nginx_node_ips)
                total_nodes += node_count
                node_ips = [node.get("nginx_node_ip", "unknown") for node in nginx_node_ips]
                self.write_log(f"Upstream {upstream_id} ({upstream_name}): {node_count} 个节点")
                self.write_log(f"  - 节点IP: {', '.join(node_ips)}")
            else:
                # 兼容旧格式：nginx_node_ip单个节点
                node_ip = meta.get("nginx_node_ip", "unknown")
                if node_ip != "unknown":
                    total_nodes += 1
                    self.write_log(f"Upstream {upstream_id} ({upstream_name}): 1 个节点")
                    self.write_log(f"  - 节点IP: {node_ip}")
        
        self.write_log(f"总节点数: {total_nodes}")
        self.write_log("=" * 60)
    
    def _execute_task(self) -> int:
        """
        执行 Nginx Upstream 同步任务逻辑
        """
        try:
            return self._execute_sync()
        except Exception as exc:
            self.write_log(f"[ERROR] 执行同步任务失败: {exc}")
            import traceback
            self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
            return 1

    def _execute_sync(self) -> int:
        """
        同步 Nginx Upstream 配置到节点
        1. 处理operator_metas（支持nginx_node_ips数组格式）
        2. 为每个upstream的所有节点生成配置文件
        3. 使用 Ansible Playbook 同步到节点
        """
        if not self.operator_metas:
            self.write_log("[ERROR] 没有有效的同步任务可执行")
            return 1
        
        self.write_log(f"准备同步 {len(self.operator_metas)} 个upstream")
        
        # 为每个upstream的所有节点生成配置文件并执行同步
        final_rc = 0
        for meta in self.operator_metas:
            if not isinstance(meta, dict):
                self.write_log(f"[WARNING] meta 不是字典类型: {type(meta)}")
                continue
            
            upstream_id = meta.get("upstream_id")
            upstream_name = meta.get("upstream_name", "unknown")
            upstream_template = meta.get("upstream_template")
            template_vars = meta.get("template_vars", {})
            
            # 支持新的nginx_node_ips数组格式
            nginx_node_ips = meta.get("nginx_node_ips", [])
            if not nginx_node_ips:
                # 兼容旧格式：nginx_node_ip单个节点
                node_id = meta.get("nginx_node_id")
                node_ip = meta.get("nginx_node_ip")
                node_port = meta.get("node_port", 22)
                if node_ip:
                    nginx_node_ips = [{
                        "nginx_node_id": node_id,
                        "nginx_node_ip": node_ip,
                        "node_port": node_port,
                    }]
                else:
                    self.write_log(f"[WARNING] upstream {upstream_name} 没有有效的nginx节点")
                    continue
            
            self.write_log(f"处理upstream {upstream_id} ({upstream_name}): {len(nginx_node_ips)} 个节点")
            node_ips = [node.get("nginx_node_ip", "unknown") for node in nginx_node_ips]
            self.write_log(f"  节点IP: {', '.join(node_ips)}")
            
            # 构建upstream配置（同一个upstream的所有节点使用相同的配置）
            upstream_meta = {
                "upstream_name": upstream_name,
                "upstream_template": upstream_template,
                "template_vars": template_vars,
            }
            
            # 生成配置文件（同一个upstream的所有节点使用相同的配置内容）
            try:
                config_content = self._generate_nginx_config([upstream_meta])
                config_file = self.work_dir / f"nginx_upstream_{upstream_id}.conf"
                config_file.write_text(config_content, encoding="utf-8")
                self.write_log(f"已生成配置文件: {config_file}")
                
                # 构建包含所有节点的inventory（同一个upstream的所有节点合并到一个inventory）
                inventory_nodes = []
                for node_info in nginx_node_ips:
                    node_ip = node_info.get("nginx_node_ip", "unknown")
                    node_port = node_info.get("node_port", 22)
                    inventory_nodes.append({
                        "ip": node_ip,
                        "port": node_port,
                    })
                
                # 构建 meta 用于生成 inventory（包含所有节点）
                inventory_meta = {
                    "service_name": f"nginx_upstream_{upstream_id}",
                    "nodes": inventory_nodes,
                }
                
                # 生成 inventory（同一个upstream的所有节点合并到一个inventory文件）
                inventory_path = self.work_dir / f"inventory_nginx_upstream_{upstream_id}.ini"
                self._generate_single_node_inventory(inventory_meta, inventory_path)
                
                # 构建 ansible vars（同一个upstream的所有节点使用相同的配置）
                ansible_vars = {
                    "upstream_config_file": str(config_file),
                    "upstream_config_content": config_content,
                }
                
                # 执行 playbook（一次性同步到所有节点）
                playbook_path = Path(__file__).parent / "ansible_playbooks" / "nginx" / "sync.yml"
                
                if not playbook_path.exists():
                    self.write_log(f"[ERROR] Playbook 不存在: {playbook_path}")
                    final_rc = 1
                    continue
                
                self.write_log(f"执行 Playbook: {playbook_path} -> upstream: {upstream_name}, 节点数: {len(nginx_node_ips)}")
                node_ips_str = ", ".join([node.get("nginx_node_ip", "unknown") for node in nginx_node_ips])
                self.write_log(f"  目标节点: {node_ips_str}")
                
                rc = self.run_ansible_playbook(
                    playbook=playbook_path,
                    inventory=inventory_path,
                    extra_vars=ansible_vars
                )
                
                if rc != 0:
                    final_rc = rc
                    self.write_log(f"[ERROR] upstream {upstream_name} 同步失败，返回码: {rc}")
                else:
                    self.write_log(f"[SUCCESS] upstream {upstream_name} 同步成功，已同步到 {len(nginx_node_ips)} 个节点")
                        
            except Exception as e:
                self.write_log(f"[ERROR] 处理upstream {upstream_name} 失败: {e}")
                import traceback
                self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
                final_rc = 1
        
        return final_rc
    
    def _generate_nginx_config(self, upstreams: List[Dict[str, Any]]) -> str:
        """
        生成 Nginx Upstream 配置文件内容
        使用 Jinja2 模板渲染每个 upstream
        """
        try:
            from jinja2 import Template
        except ImportError:
            self.write_log("[ERROR] 未安装 jinja2，请安装: pip install jinja2")
            raise
        
        config_lines = []
        config_lines.append("# Nginx Upstream 配置文件")
        config_lines.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        config_lines.append("")
        
        for meta in upstreams:
            upstream_name = meta.get("upstream_name", "unknown")
            upstream_template = meta.get("upstream_template")
            template_vars = meta.get("template_vars", {})
            
            if not upstream_template:
                # 使用默认模板
                upstream_template = """upstream {{ service_name }}_upstream {
{% for host in hosts %}
    server {{ host.ip }}:{{ host.port }}{% if host.status == 'down' %} down{% endif %};
{% endfor %}
}"""
            
            try:
                template = Template(upstream_template)
                rendered = template.render(**template_vars)
                config_lines.append(rendered)
                config_lines.append("")
                self.write_log(f"渲染 upstream {upstream_name} 成功")
            except Exception as e:
                self.write_log(f"[ERROR] 渲染 upstream {upstream_name} 失败: {e}")
                # 使用默认配置
                config_lines.append(f"# upstream {upstream_name} (渲染失败，使用默认配置)")
                config_lines.append(f"upstream {upstream_name} {{")
                config_lines.append("    # 配置生成失败")
                config_lines.append("}")
                config_lines.append("")
        
        return "\n".join(config_lines)
    
    def _generate_single_node_inventory(self, meta: Dict[str, Any], inventory_path: Path) -> None:
        """
        为单个节点生成 Ansible Inventory
        """
        if not isinstance(meta, dict):
            raise ValueError("meta 必须是字典类型")
        
        group_name = meta.get("service_name", "nginx_node")
        safe_group = group_name.replace(" ", "_")
        nodes = meta.get("nodes", [])
        
        if not nodes:
            raise ValueError("nodes 不能为空")
        
        lines: List[str] = []
        default_user = os.environ.get("ANSIBLE_SSH_USER", "root")
        
        lines.append(f"[{safe_group}]")
        for node in nodes:
            if isinstance(node, dict):
                host = node.get("ip") or node.get("host")
                port = node.get("port", 22)
                user = node.get("ansible_user") or default_user
                password = node.get("ansible_password")
            else:
                host = getattr(node, "ip", None)
                port = getattr(node, "port", 22)
                user = getattr(node, "ansible_user", default_user)
                password = getattr(node, "ansible_password", None)
            
            if not host:
                continue
            
            alias = f"{safe_group}_{host}_{port}"
            vars_parts = [f"ansible_host={host}", f"ansible_port={port}", f"ansible_user={user}"]
            if password:
                vars_parts.append(f"ansible_password={password}")
            extra_vars = " ".join(vars_parts)
            lines.append(f"{alias} {extra_vars}")
        
        # 增加组变量支持
        group_vars = meta.get("ansible_vars")
        if group_vars and isinstance(group_vars, dict):
            lines.append(f"[{safe_group}:vars]")
            for k, v in group_vars.items():
                if isinstance(v, str):
                    lines.append(f"{k}={v}")
                else:
                    lines.append(f"{k}={json.dumps(v, ensure_ascii=False)}")
        
        inventory_path.write_text("\n".join(lines), encoding="utf-8")
        self.write_log(f"已生成 Ansible Inventory: {inventory_path}")


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
    在当前进程中执行 Nginx Upstream 同步任务
    """
    executor = NginxUpstreamSyncTaskExecutor(
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

