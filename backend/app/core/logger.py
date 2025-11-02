# -*- coding: utf-8 -*-

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.config.setting import settings


class AppLogger:
    """应用级日志管理器：一次性配置 + 获取。"""

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._configured = False

    def _create_file_handler(self, stem: str, level: int, log_dir: Path, formatter: logging.Formatter) -> TimedRotatingFileHandler:
        file_path = log_dir / f"{stem}.log"
        handler = TimedRotatingFileHandler(
            filename=str(file_path),
            when=settings.WHEN,
            interval=settings.INTERVAL,
            backupCount=settings.BACKUPCOUNT,
            encoding=settings.ENCODING,
        )
        handler.setLevel(level)
        handler.setFormatter(formatter)
        handler.suffix = "%Y-%m-%d.log"

        def namer(default_name: str) -> str:
            parts = Path(default_name).name.split(".")
            if len(parts) >= 3 and parts[-1] == "log":
                ts = parts[-2]
                return str(Path(default_name).with_name(f"{stem}_{ts}.log"))
            return default_name

        handler.namer = namer
        return handler

    def _install_excepthook(self) -> None:
        def excepthook(exc_type, exc_value, exc_tb):
            if issubclass(exc_type, KeyboardInterrupt):
                return
            self._logger.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_tb))

        sys.excepthook = excepthook

    def configure(self) -> logging.Logger:
        if self._configured:
            return self._logger

        # 基础设置
        self._logger.setLevel(settings.LOGGER_LEVEL)
        self._logger.handlers.clear()
        self._logger.propagate = False

        # 目录与格式
        log_dir = Path(settings.LOGGER_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter(settings.LOGGER_FORMAT)

        # 文件处理器
        self._logger.addHandler(self._create_file_handler("info", logging.INFO, log_dir, formatter))
        self._logger.addHandler(self._create_file_handler("error", logging.ERROR, log_dir, formatter))

        # 控制台处理器
        console = logging.StreamHandler()
        console.setLevel(settings.LOGGER_LEVEL)
        console.setFormatter(formatter)
        self._logger.addHandler(console)

        # 全局异常钩子
        self._install_excepthook()

        self._configured = True
        return self._logger

    def get_logger(self) -> logging.Logger:
        return self.configure()

def get_logger() -> logging.Logger:
    AL = AppLogger()
    return AL.get_logger()


# 模块级兼容实例
logger = get_logger()
