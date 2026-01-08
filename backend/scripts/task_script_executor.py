# -*- coding: utf-8 -*-
"""
脚本执行任务执行器
支持 Python 和 Shell 脚本的执行
"""

import json
import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from base_batch_task_executor import BaseBatchTaskExecutor


class ScriptExecutorTaskExecutor(BaseBatchTaskExecutor):
    """脚本执行任务执行器"""
    
    def print_init_info(self):
        """打印初始化信息"""
        super().print_init_info()
        
        if not self.operator_metas:
            self.write_log("[WARNING] operator_metas 为空")
            self.write_log("=" * 60)
            return
        
        self.write_log(f"脚本数量: {len(self.operator_metas)}")
        
        for idx, meta in enumerate(self.operator_metas, 1):
            if not isinstance(meta, dict):
                self.write_log(f"[WARNING] 脚本 {idx} 不是字典类型: {type(meta)}")
                continue
            
            script_id = meta.get("script_id")
            script_name = meta.get("script_name", f"脚本ID:{script_id}")
            script_type = meta.get("script_type", "unknown")
            content_type = meta.get("content_type", "text")
            params = meta.get("params", {})
            
            self.write_log(f"脚本 {idx}: {script_name} (ID:{script_id})")
            self.write_log(f"  - 类型: {script_type}")
            self.write_log(f"  - 内容类型: {content_type}")
            self.write_log(f"  - 参数: {json.dumps(params, ensure_ascii=False)}")
        
        self.write_log("=" * 60)
    
    def _execute_task(self) -> int:
        """执行脚本任务"""
        try:
            if self.task_type == "run":
                return self._execute_run()
            
            self.write_log(f"[ERROR] 未知任务类型: {self.task_type}")
            return 1
        except Exception as exc:
            self.write_log(f"[ERROR] 执行脚本任务失败: {exc}")
            import traceback
            self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
            return 1

    def _execute_run(self) -> int:
        """执行脚本"""
        if not self.operator_metas:
            self.write_log("[ERROR] 没有脚本可执行")
            return 1
        
        total_scripts = len(self.operator_metas)
        success_count = 0
        failed_count = 0
        
        for idx, meta in enumerate(self.operator_metas, 1):
            script_name = meta.get("script_name", f"脚本{idx}")
            script_type = meta.get("script_type", "shell")
            content_type = meta.get("content_type", "text")
            content = meta.get("content", "")
            params = meta.get("params", {})
            
            self.write_log(f"\n{'='*60}")
            self.write_log(f"开始执行脚本 [{idx}/{total_scripts}]: {script_name}")
            self.write_log(f"{'='*60}")
            
            # 计算进度
            progress = int((idx - 1) / total_scripts * 100)
            self.output_progress(progress, f"正在执行: {script_name}")
            
            try:
                # 准备脚本文件
                script_path = self._prepare_script(
                    script_name=script_name,
                    script_type=script_type,
                    content_type=content_type,
                    content=content
                )
                
                # 执行脚本
                rc = self._run_script(
                    script_path=script_path,
                    script_type=script_type,
                    params=params
                )
                
                if rc == 0:
                    success_count += 1
                    self.write_log(f"[SUCCESS] 脚本 {script_name} 执行成功")
                else:
                    failed_count += 1
                    self.write_log(f"[FAILED] 脚本 {script_name} 执行失败，返回码: {rc}")
                    
            except Exception as e:
                failed_count += 1
                self.write_log(f"[ERROR] 脚本 {script_name} 执行异常: {e}")
                import traceback
                self.write_log(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}")
        
        # 输出最终结果
        self.write_log(f"\n{'='*60}")
        self.write_log(f"脚本执行完成")
        self.write_log(f"  - 总数: {total_scripts}")
        self.write_log(f"  - 成功: {success_count}")
        self.write_log(f"  - 失败: {failed_count}")
        self.write_log(f"{'='*60}")
        
        self.output_progress(100, f"执行完成: 成功{success_count}/失败{failed_count}")
        
        # 返回码：全部成功返回0，部分成功返回2，全部失败返回1
        if failed_count == 0:
            return 0
        elif success_count > 0:
            return 2  # 部分成功
        else:
            return 1  # 全部失败

    def _prepare_script(
        self,
        script_name: str,
        script_type: str,
        content_type: str,
        content: str
    ) -> Path:
        """
        准备脚本文件
        
        Args:
            script_name: 脚本名称
            script_type: 脚本类型 (python/shell)
            content_type: 内容类型 (text/local_path)
            content: 脚本内容或本地路径
        
        Returns:
            Path: 脚本文件路径
        """
        if content_type == "local_path":
            # 本地路径模式
            script_path = Path(content)
            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_path}")
            return script_path
        
        # 文本内容模式 - 创建临时脚本文件
        ext = ".py" if script_type == "python" else ".sh"
        safe_name = script_name.replace(" ", "_").replace("/", "_")
        script_file = self.work_dir / f"script_{safe_name}_{self.task_id}{ext}"
        
        # 如果是 Python 脚本，检查并添加编码声明（如果还没有）
        if script_type == "python":
            # 检查是否已有编码声明
            content_lines = content.split("\n")
            has_encoding = any(
                line.strip().startswith("#") and ("coding" in line.lower() or "encoding" in line.lower())
                for line in content_lines[:2]
            )
            if not has_encoding:
                # 在文件开头添加 UTF-8 编码声明
                content = f"# -*- coding: utf-8 -*-\n{content}"
        
        # 写入脚本内容（确保使用 UTF-8 编码）
        script_file.write_text(content, encoding="utf-8")
        
        # 设置可执行权限（Linux/Unix）
        if os.name != "nt":
            os.chmod(script_file, 0o755)
        
        self.write_log(f"已创建临时脚本文件: {script_file}")
        return script_file

    def _run_script(
        self,
        script_path: Path,
        script_type: str,
        params: Dict[str, Any]
    ) -> int:
        """
        执行脚本
        
        Args:
            script_path: 脚本文件路径
            script_type: 脚本类型 (python/shell)
            params: 脚本参数
        
        Returns:
            int: 返回码
        """
        # 构建命令
        if script_type == "python":
            python_bin = os.environ.get("PYTHON_BIN", sys.executable)
            # 使用 -u 参数禁用 Python 输出缓冲，确保实时输出
            cmd = [python_bin, "-u", str(script_path)]
        else:
            # shell 脚本
            shell_bin = os.environ.get("SHELL_BIN", "/bin/bash")
            if os.name == "nt":
                shell_bin = os.environ.get("SHELL_BIN", "bash")
            cmd = [shell_bin, str(script_path)]
        
        # 将参数作为环境变量传递
        env_override = {}
        for key, value in params.items():
            env_key = f"SCRIPT_PARAM_{key.upper()}"
            if isinstance(value, (dict, list)):
                env_override[env_key] = json.dumps(value, ensure_ascii=False)
            else:
                env_override[env_key] = str(value)
        
        # 同时将参数作为 JSON 传递
        env_override["SCRIPT_PARAMS_JSON"] = json.dumps(params, ensure_ascii=False)
        
        # 设置 Python 无缓冲环境变量，确保实时输出
        env_override["PYTHONUNBUFFERED"] = "1"
        
        # 设置 Python IO 编码为 UTF-8，解决中文乱码问题
        env_override["PYTHONIOENCODING"] = "utf-8"
        
        self.write_log(f"执行命令: {' '.join(cmd)}")
        if params:
            self.write_log(f"脚本参数: {json.dumps(params, ensure_ascii=False)}")
        
        return self.run_command(cmd, cwd=self.work_dir, env_override=env_override)


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
    在当前进程中执行脚本任务
    """
    executor = ScriptExecutorTaskExecutor(
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


