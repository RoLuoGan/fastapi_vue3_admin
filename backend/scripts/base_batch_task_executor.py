# -*- coding: utf-8 -*-
"""
批次任务执行器基类
所有任务执行器都应该继承此类
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

import json
import os
import subprocess
import tempfile

import oss2


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
    ) -> None:
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
        self.ansible_bin = os.environ.get("ANSIBLE_BIN", "ansible")
        self.ansible_playbook_bin = os.environ.get("ANSIBLE_PLAYBOOK_BIN", "ansible-playbook")
        # 当前工作目录
        self.work_dir = Path(
            os.environ.get(
                "BATCH_WORK_DIR",
                Path.cwd() / "workspace" / f"batch_task_{self.task_id}",
            )
        )
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._oss_bucket: Optional[oss2.Bucket] = None
        self._oss_config_cache: Optional[Dict[str, str]] = None
        
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

    # ------------------------------------------------------------------
    # OSS 能力
    # ------------------------------------------------------------------
    def _load_oss_config(self) -> Dict[str, str]:
        """
        尝试从环境变量、JSON 配置或当前目录配置文件中加载 OSS 连接信息。
        """
        if self._oss_config_cache:
            return self._oss_config_cache
        
        config: Dict[str, str] = {}
        
        # 1. 尝试从当前目录配置文件加载
        config_file = Path(__file__).parent / "oss_config.json"
        if config_file.exists():
            try:
                self.write_log(f"加载 OSS 配置文件: {config_file}")
                config = json.loads(config_file.read_text(encoding="utf-8"))
            except Exception as e:
                self.write_log(f"[WARNING] OSS 配置文件解析失败: {e}")

        # 2. 尝试从环境变量 JSON 加载 (覆盖配置文件)
        config_json = os.environ.get("OSS_CONFIG_JSON")
        if config_json:
            try:
                env_config = json.loads(config_json)
                config.update(env_config)
            except json.JSONDecodeError:
                self.write_log("[WARNING] OSS_CONFIG_JSON 解析失败")
        
        env_mapping = {
            "access_key_id": ["OSS_ACCESS_KEY_ID", "ALIYUN_OSS_ACCESS_KEY_ID"],
            "access_key_secret": ["OSS_ACCESS_KEY_SECRET", "ALIYUN_OSS_ACCESS_KEY_SECRET"],
            "endpoint": ["OSS_ENDPOINT", "ALIYUN_OSS_ENDPOINT"],
            "bucket": ["OSS_BUCKET_NAME", "ALIYUN_OSS_BUCKET_NAME", "OSS_BUCKET"],
        }
        
        # 3. 尝试从单独环境变量加载 (覆盖之前的配置)
        for key, candidates in env_mapping.items():
            if key not in config or not config[key]:
                for env_key in candidates:
                    value = os.environ.get(env_key)
                    if value:
                        config[key] = value
                        break
        
        missing = [k for k, v in config.items() if not v]
        # 检查必要字段 (简化检查逻辑)
        required_keys = ["access_key_id", "access_key_secret", "endpoint", "bucket"]
        missing = [k for k in required_keys if k not in config or not config[k]]
        
        if missing:
            raise RuntimeError(f"缺少 OSS 配置项: {missing}. 请在环境变量、OSS_CONFIG_JSON 或 oss_config.json 中提供。")
        
        # 规范化 endpoint
        endpoint = config["endpoint"]
        if endpoint.startswith("http://"):
            endpoint = endpoint[7:]
        elif endpoint.startswith("https://"):
            endpoint = endpoint[8:]
        endpoint = endpoint.rstrip("/")
        config["endpoint"] = endpoint
        
        self._oss_config_cache = config
        return config
    
    def _get_oss_bucket(self) -> oss2.Bucket:
        if self._oss_bucket:
            return self._oss_bucket
        
        config = self._load_oss_config()
        self.write_log(f"初始化 OSS 客户端 -> Endpoint: {config['endpoint']} Bucket: {config['bucket']}")
        auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
        bucket = oss2.Bucket(auth, config["endpoint"], config["bucket"])
        self._oss_bucket = bucket
        return bucket
    
    def download_oss_object(self, object_key: str, *, target_path: Optional[Path] = None, overwrite: bool = True) -> Path:
        """
        从 OSS 下载文件到工作目录。
        """
        key = object_key.lstrip("/")
        filename = target_path or (self.work_dir / Path(key).name)
        filename.parent.mkdir(parents=True, exist_ok=True)
        
        if filename.exists() and not overwrite:
            self.write_log(f"[OSS] 文件已存在，跳过下载: {filename}")
            return filename
        
        bucket = self._get_oss_bucket()
        self.write_log(f"[OSS] 下载对象: {key} -> {filename}")
        result = bucket.get_object(key)
        with open(filename, "wb") as f:
            f.write(result.read())
        self.write_log(f"[OSS] 下载完成，大小: {filename.stat().st_size} 字节")
        return filename

    # ------------------------------------------------------------------
    # Ansible辅助能力
    # ------------------------------------------------------------------
    def generate_ansible_inventory(self, metas: List[Dict[str, Any]], inventory_name: Optional[str] = None) -> Path:
        """
        根据操作元数据动态生成 Ansible inventory。
        """
        if not metas:
            raise ValueError("operator_metas 为空，无法生成 Ansible Inventory")
        
        inventory_path = self.work_dir / (inventory_name or f"inventory_{self.task_id}.ini")
        lines: List[str] = []
        default_user = os.environ.get("ANSIBLE_SSH_USER", "root")
        
        for meta in metas:
            if not isinstance(meta, dict):
                continue
            group_name = meta.get("service_name") or f"service_{meta.get('service_id')}"
            safe_group = group_name.replace(" ", "_")
            nodes = meta.get("nodes", [])
            if not nodes:
                continue
            
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
                
                # 生成动态别名：{模块名}_{ip}_{port}
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
                     lines.append(f"{k}={v}")
            
            lines.append("")  # 分隔
        
        inventory_path.write_text("\n".join(lines), encoding="utf-8")
        self.write_log(f"已生成 Ansible Inventory: {inventory_path}")
        return inventory_path

    # ------------------------------------------------------------------
    # 命令执行能力
    # ------------------------------------------------------------------
    def run_command(
        self,
        cmd: List[str],
        *,
        cwd: Optional[Path] = None,
        env_override: Optional[Dict[str, Any]] = None,
        redacted_args: Optional[List[int]] = None,
    ) -> int:
        """
        运行本地命令，并将输出写入日志。
        """
        display_cmd = cmd.copy()
        if redacted_args:
            for idx in redacted_args:
                if 0 <= idx < len(display_cmd):
                    display_cmd[idx] = "***"
        self.write_log(f"[CMD] {' '.join(display_cmd)}")
        
        env = os.environ.copy()
        if env_override:
            env.update({k: str(v) for k, v in env_override.items() if v is not None})
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        
        if process.stdout:
            for raw_line in iter(process.stdout.readline, ""):
                line = raw_line.rstrip("\r\n")
                if line:
                    self.write_log(f"[命令输出] {line}")
            process.stdout.close()
        
        return_code = process.wait()
        if return_code == 0:
            self.write_log("[CMD] 命令执行完成")
        else:
            self.write_log(f"[CMD] 命令执行失败，退出码: {return_code}")
        return return_code
    
    def run_ansible_command(
        self,
        args: List[str],
        *,
        cwd: Optional[Path] = None,
        env_override: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        执行 ansible 命令（默认使用 ad-hoc 模式）。
        """
        cmd = [self.ansible_bin] + args
        return self.run_command(cmd, cwd=cwd, env_override=env_override)

    def run_ansible_playbook(
        self,
        playbook: Path | str,
        *,
        inventory: Path,
        extra_vars: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        env_override: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        执行 ansible-playbook。
        优化：使用临时文件传递 extra_vars，避免 Windows 命令行编码问题。
        """
        playbook_path = Path(playbook)
        if not playbook_path.exists():
            raise FileNotFoundError(f"未找到 playbook 文件: {playbook_path}")

        cmd = [
            self.ansible_playbook_bin,
            "-i",
            str(inventory),
            str(playbook_path),
        ]

        # 使用临时文件传递 extra_vars，避免 Windows 命令行 JSON 编码问题
        extra_vars_file = None
        if extra_vars:
            try:
                # 创建临时 JSON 文件
                extra_vars_file = self.work_dir / f"extra_vars_{self.task_id}_{id(extra_vars)}.json"
                with open(extra_vars_file, "w", encoding="utf-8") as f:
                    json.dump(extra_vars, f, ensure_ascii=False, indent=2)
                cmd += ["--extra-vars", f"@{extra_vars_file}"]
            except Exception as e:
                self.write_log(f"[WARN] 创建 extra_vars 临时文件失败，回退到命令行参数: {e}")
                # 回退到命令行参数方式
                cmd += ["--extra-vars", json.dumps(extra_vars, ensure_ascii=False)]
        
        if tags:
            cmd += ["--tags", ",".join(tags)]

        try:
            return self.run_command(cmd, env_override=env_override)
        finally:
            # 清理临时文件
            if extra_vars_file and extra_vars_file.exists():
                try:
                    extra_vars_file.unlink()
                except Exception:
                    pass  # 忽略清理错误

