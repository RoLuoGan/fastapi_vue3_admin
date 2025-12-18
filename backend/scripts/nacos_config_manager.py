# -*- coding: utf-8 -*-
"""
nacos配置管理工具
提供以下功能：
1. 将目录下的所有配置文件上传到nacos, 可以按照文件夹名上传, 也可以按照文件名上传, 文件名作为data_id, 文件内容作为配置内容
 可以指定namespace不指定则使用默认namespace
 可以指定group不指定则文件夹名作为group
 支持文件递归, 支持覆盖上传, 支持增量上传
2. 将group所有的配置文件下载到目录下, 可以指定group, namespace, data_id, 支持文件递归, 支持覆盖下载
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="Nacos配置管理工具")
console = Console()


class NacosConfigManager:
    """Nacos配置管理器（使用HTTP API）"""
    
    def __init__(
        self,
        server_addresses: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        namespace: Optional[str] = None,
    ):
        """
        初始化Nacos客户端配置
        
        Args:
            server_addresses: Nacos服务器地址，格式: "ip1:port1,ip2:port2" 或 "ip:port"
            username: 用户名（可选）
            password: 密码（可选）
            namespace: 命名空间ID（可选，默认使用public命名空间）
        """
        self.server_addresses = server_addresses
        self.username = username
        self.password = password
        self.namespace = namespace or "public"
        
        # 解析服务器地址（取第一个）
        server_addr = server_addresses.split(",")[0].strip()
        if ":" not in server_addr:
            server_addr = f"{server_addr}:8848"
        
        # 构建基础URL（使用 Open API 而不是 Admin API）
        self.base_url = f"http://{server_addr}/nacos/v1/cs"
        self.admin_base_url = f"http://{server_addr}/nacos/v3/admin/cs"
        
        # 认证信息（Open API 使用 query 参数，Admin API 使用 Basic Auth）
        self.auth = None
        if username and password:
            self.auth = (username, password)
            self.username_param = username
            self.password_param = password
        else:
            self.username_param = None
            self.password_param = None
        
        # accessToken 缓存（用于 Admin API）
        self._access_token: Optional[str] = None
    
    @staticmethod
    def _encode_data_id(path: str) -> str:
        """
        将文件路径编码为 Nacos 支持的 dataId 格式
        Nacos dataId 不支持路径分隔符，将 / 替换为 __ (双下划线)
        
        Args:
            path: 文件路径，如 "java/deploy.yml"
        
        Returns:
            编码后的 dataId，如 "java__deploy.yml"
        """
        return path.replace("/", "__").replace("\\", "__")
    
    @staticmethod
    def _decode_data_id(data_id: str) -> str:
        """
        将 Nacos dataId 解码为文件路径格式
        将 __ (双下划线) 还原为 /
        
        Args:
            data_id: Nacos dataId，如 "java__deploy.yml"
        
        Returns:
            解码后的路径，如 "java/deploy.yml"
        """
        return data_id.replace("__", "/")
    
    async def _get_access_token(self) -> Optional[str]:
        """
        获取 accessToken（用于 Admin API 认证）
        
        Returns:
            accessToken 字符串，如果获取失败返回 None
        """
        if self._access_token:
            return self._access_token
        
        if not self.username_param or not self.password_param:
            return None
        
        # 使用 Open API 登录接口获取 accessToken
        server_addr = self.server_addresses.split(",")[0].strip()
        if ":" not in server_addr:
            server_addr = f"{server_addr}:8848"
        url = f"http://{server_addr}/nacos/v1/auth/login"
        params = {
            "username": self.username_param,
            "password": self.password_param,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, params=params)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("accessToken"):
                        self._access_token = result["accessToken"]
                        return self._access_token
                    else:
                        console.print(f"[yellow]获取 accessToken 失败: {result.get('message', '未知错误')}[/yellow]")
                        return None
                else:
                    console.print(f"[yellow]登录失败: HTTP {response.status_code}, {response.text[:200]}[/yellow]")
                    return None
        except Exception as e:
            console.print(f"[yellow]获取 accessToken 异常: {e}[/yellow]")
            return None
    
    async def _get_config(
        self,
        data_id: str,
        group: str,
        namespace: Optional[str] = None,
    ) -> Optional[str]:
        """
        获取配置内容（使用 Open API）
        
        Args:
            data_id: 配置ID
            group: 配置组名
            namespace: 命名空间ID（Open API 中使用 tenant 参数）
        
        Returns:
            配置内容，如果不存在返回None
        """
        namespace = namespace or self.namespace
        if namespace == "public":
            namespace = ""  # Open API 中 public 命名空间使用空字符串
        
        url = f"{self.base_url}/configs"
        params = {
            "dataId": data_id,
            "group": group,
            "tenant": namespace if namespace else "",
        }
        
        # Open API 使用 query 参数传递用户名密码
        if self.username_param and self.password_param:
            params["username"] = self.username_param
            params["password"] = self.password_param
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    # Open API 直接返回配置内容（字符串），不是 JSON
                    content = response.text
                    if content:
                        return content
                    return None
                elif response.status_code == 404:
                    return None
                else:
                    console.print(f"[yellow]获取配置失败: HTTP {response.status_code}, {response.text[:200]}[/yellow]")
                    return None
        except Exception as e:
            console.print(f"[yellow]获取配置异常: {e}[/yellow]")
            return None
    
    async def _publish_config(
        self,
        data_id: str,
        group: str,
        content: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """
        发布配置（使用 Open API）
        
        Args:
            data_id: 配置ID
            group: 配置组名
            content: 配置内容
            namespace: 命名空间ID（Open API 中使用 tenant 参数）
        
        Returns:
            是否成功
        """
        namespace = namespace or self.namespace
        if namespace == "public":
            namespace = ""  # Open API 中 public 命名空间使用空字符串
        
        url = f"{self.base_url}/configs"
        params = {
            "dataId": data_id,
            "group": group,
            "tenant": namespace if namespace else "",
        }
        
        # Open API 使用 query 参数传递用户名密码
        if self.username_param and self.password_param:
            params["username"] = self.username_param
            params["password"] = self.password_param
        
        # content 作为 form 数据发送
        data = {
            "content": content,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, params=params, data=data)
                
                if response.status_code == 200:
                    # Open API 返回 "true" 字符串表示成功
                    result_text = response.text.strip()
                    if result_text == "true" or result_text.lower() == "true":
                        return True
                    else:
                        raise Exception(f"发布配置失败: {result_text}")
                else:
                    error_text = response.text[:500]
                    raise Exception(f"HTTP {response.status_code}: {error_text}")
        except httpx.HTTPError as e:
            raise Exception(f"网络请求失败: {e}")
    
    async def _list_configs(
        self,
        group: Optional[str] = None,
        namespace: Optional[str] = None,
        page_no: int = 1,
        page_size: int = 1000,
    ) -> List[tuple]:
        """
        获取配置列表（使用 Admin API，需要 accessToken）
        
        Args:
            group: 配置组名（可选）
            namespace: 命名空间ID（可选）
            page_no: 页码
            page_size: 每页大小
        
        Returns:
            配置列表，格式: [(data_id, group_name), ...]
        """
        namespace = namespace or self.namespace
        
        # 获取 accessToken
        access_token = await self._get_access_token()
        if not access_token:
            console.print("[yellow]无法获取 accessToken，列表查询可能需要管理员权限[/yellow]")
        
        url = f"{self.admin_base_url}/config/list"
        params = {
            "pageNo": page_no,
            "pageSize": page_size,
            "namespaceId": namespace,
        }
        
        if group:
            params["groupName"] = group
        
        # 构建请求头，使用 accessToken
        headers = {}
        if access_token:
            headers["accessToken"] = access_token
        
        configs = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0 and result.get("data"):
                        page_items = result["data"].get("pageItems", [])
                        configs = [
                            (item["dataId"], item["groupName"])
                            for item in page_items
                        ]
                        
                        # 如果还有更多页，继续获取
                        total_count = result["data"].get("totalCount", 0)
                        pages_available = result["data"].get("pagesAvailable", 1)
                        
                        if pages_available > page_no:
                            # 递归获取后续页面
                            next_configs = await self._list_configs(
                                group=group,
                                namespace=namespace,
                                page_no=page_no + 1,
                                page_size=page_size,
                            )
                            configs.extend(next_configs)
                        
                        return configs
                    else:
                        error_msg = result.get("message", "未知错误")
                        console.print(f"[yellow]获取配置列表失败: {error_msg}[/yellow]")
                        return []
                else:
                    error_text = response.text[:500]
                    console.print(f"[yellow]获取配置列表失败: HTTP {response.status_code}, {error_text}[/yellow]")
                    return []
        except Exception as e:
            console.print(f"[yellow]获取配置列表异常: {e}[/yellow]")
            return []
    
    async def upload_configs(
        self,
        config_dir: Path,
        group: Optional[str] = None,
        namespace: Optional[str] = None,
        recursive: bool = True,
        overwrite: bool = False,
        incremental: bool = False,
        use_folder_as_group: bool = True,
    ) -> Dict[str, int]:
        """
        上传配置文件到Nacos
        
        Args:
            config_dir: 配置文件目录
            group: 配置组名（可选，如果不指定则使用顶层目录名）
            namespace: 命名空间ID（可选，默认使用初始化时的namespace）
            recursive: 是否递归遍历子目录
            overwrite: 是否覆盖已存在的配置
            incremental: 是否增量上传（只上传不存在的配置）
            use_folder_as_group: 保留参数（不再按子目录拆分 group）
        
        Returns:
            统计信息字典: {"success": 成功数量, "failed": 失败数量, "skipped": 跳过数量}
        """
        config_dir = Path(config_dir).resolve()
        if not config_dir.exists():
            raise FileNotFoundError(f"配置目录不存在: {config_dir}")
        
        namespace = namespace or self.namespace
        stats = {"success": 0, "failed": 0, "skipped": 0}
        failed_files = []
        
        # 计算默认 group（用顶层目录名）
        default_group = group or config_dir.name

        # 获取所有配置文件
        pattern = "**/*" if recursive else "*"
        config_files = list(config_dir.glob(pattern))
        config_files = [f for f in config_files if f.is_file()]
        
        console.print(f"[green]找到 {len(config_files)} 个配置文件[/green]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("上传配置...", total=len(config_files))
            
            for config_file in config_files:
                try:
                    # 确定group：使用顶层目录名或显式传入值
                    file_group = default_group

                    # 确定data_id：使用相对路径，避免不同目录同名覆盖
                    rel_path = config_file.relative_to(config_dir)
                    original_data_id = rel_path.as_posix()
                    # 编码 data_id（将路径分隔符替换为双下划线）
                    encoded_data_id = self._encode_data_id(original_data_id)
                    
                    # 读取文件内容
                    content = config_file.read_text(encoding="utf-8")

                    # 打印上传配置信息（显示原始路径）
                    console.print(f"[cyan]上传配置: {original_data_id} (group: {file_group})[/cyan]")
                    
                    # 检查是否已存在（增量上传模式）
                    if incremental:
                        existing_content = await self._get_config(
                            data_id=encoded_data_id,
                            group=file_group,
                            namespace=namespace,
                        )
                        if existing_content is not None:
                            console.print(f"[yellow]配置已存在: {original_data_id} (group: {file_group})[/yellow]")
                            stats["skipped"] += 1
                            progress.update(task, advance=1)
                            continue
                    
                    # 检查是否已存在（非覆盖模式）
                    if not overwrite and not incremental:
                        existing_content = await self._get_config(
                            data_id=encoded_data_id,
                            group=file_group,
                            namespace=namespace,
                        )
                        if existing_content is not None:
                            console.print(f"[yellow]配置已存在: {original_data_id} (group: {file_group})[/yellow]")
                            stats["skipped"] += 1
                            progress.update(task, advance=1)
                            continue
                    
                    # 发布配置
                    await self._publish_config(
                        data_id=encoded_data_id,
                        group=file_group,
                        content=content,
                        namespace=namespace,
                    )
                    
                    console.print(f"[green]上传成功: {original_data_id} (group: {file_group})[/green]")
                    
                    stats["success"] += 1
                    progress.update(
                        task,
                        advance=1,
                        description=f"已上传: {original_data_id} (group: {file_group})"
                    )
                    
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    # 使用原始路径显示错误
                    original_path = str(config_file.relative_to(config_dir))
                    console.print(f"[red]上传失败: {original_path} (group: {file_group})[/red]: {error_msg}")

                    stats["failed"] += 1
                    failed_files.append((str(config_file), error_msg))
                    progress.update(
                        task,
                        advance=1,
                        description=f"上传失败: {config_file.name}"
                    )
        
        if failed_files:
            console.print("\n[red]上传失败的文件:[/red]")
            for file_path, error in failed_files:
                console.print(f"  [red]{file_path}[/red]: {error}")
        
        return stats
    
    async def download_configs(
        self,
        output_dir: Path,
        group: Optional[str] = None,
        namespace: Optional[str] = None,
        data_id: Optional[str] = None,
        recursive: bool = False,
        overwrite: bool = False,
    ) -> Dict[str, int]:
        """
        从Nacos下载配置文件
        
        Args:
            output_dir: 输出目录
            group: 配置组名（可选，如果不指定则下载所有group）
            namespace: 命名空间ID（可选，默认使用初始化时的namespace）
            data_id: 配置ID（可选，如果不指定则下载指定group的所有配置）
            recursive: 是否递归下载（暂不支持，保留接口）
            overwrite: 是否覆盖已存在的文件
        
        Returns:
            统计信息字典: {"success": 成功数量, "failed": 失败数量, "skipped": 跳过数量}
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        namespace = namespace or self.namespace
        stats = {"success": 0, "failed": 0, "skipped": 0}
        failed_configs = []
        
        try:
            # 如果指定了data_id，直接下载单个配置
            if data_id:
                # 如果用户输入的是路径格式，需要编码
                encoded_data_id = self._encode_data_id(data_id)
                configs_to_download = [(encoded_data_id, group or "DEFAULT_GROUP")]
                console.print(f"[cyan]直接下载指定配置: {data_id} (group: {group or 'DEFAULT_GROUP'})[/cyan]")
            else:
                # 获取配置列表
                console.print(f"[cyan]正在获取配置列表...[/cyan]")
                console.print(f"  命名空间: {namespace}")
                if group:
                    console.print(f"  组名: {group}")
                else:
                    console.print("[yellow]警告: 未指定group，将尝试获取所有配置[/yellow]")
                
                configs_to_download = await self._list_configs(
                    group=group,
                    namespace=namespace,
                )
                
                if not configs_to_download:
                    console.print("[yellow]未找到需要下载的配置[/yellow]")
                    return stats
                
                console.print(f"[green]成功获取配置列表，共 {len(configs_to_download)} 个配置[/green]")
            
            console.print(f"[green]找到 {len(configs_to_download)} 个配置[/green]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("下载配置...", total=len(configs_to_download))
                
                for data_id_item, group_item in configs_to_download:
                    try:
                        # 解码 data_id（还原路径分隔符）
                        decoded_data_id = self._decode_data_id(data_id_item)
                        
                        # 获取配置内容
                        console.print(f"[cyan]正在下载: {decoded_data_id} (group: {group_item})[/cyan]")
                        
                        content = await self._get_config(
                            data_id=data_id_item,  # 使用编码后的 data_id 查询
                            group=group_item,
                            namespace=namespace,
                        )
                        
                        if content is None:
                            console.print(f"[yellow]配置内容为空或不存在: {decoded_data_id} (group: {group_item})[/yellow]")
                            stats["skipped"] += 1
                            progress.update(task, advance=1)
                            continue
                        
                        # 确定输出文件路径（使用 group 作为父目录，然后是解码后的路径）
                        if group_item and group_item != "DEFAULT_GROUP":
                            output_file = output_dir / group_item / decoded_data_id
                        else:
                            output_file = output_dir / decoded_data_id
                        
                        # 检查文件是否存在
                        if output_file.exists() and not overwrite:
                            console.print(f"[yellow]文件已存在，跳过: {output_file}[/yellow]")
                            stats["skipped"] += 1
                            progress.update(task, advance=1)
                            continue
                        
                        # 创建目录并写入文件
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        output_file.write_text(content, encoding="utf-8")
                        
                        console.print(f"[green]成功下载: {decoded_data_id} -> {output_file}[/green]")
                        stats["success"] += 1
                        progress.update(
                            task,
                            advance=1,
                            description=f"已下载: {decoded_data_id} (group: {group_item})"
                        )
                        
                    except Exception as e:
                        error_msg = f"{type(e).__name__}: {str(e)}"
                        # 尝试解码显示，如果失败则显示原始 data_id
                        try:
                            display_name = self._decode_data_id(data_id_item)
                        except:
                            display_name = data_id_item
                        console.print(f"[red]下载失败: {display_name} (group: {group_item})[/red]")
                        console.print(f"[red]错误详情: {error_msg}[/red]")
                        
                        # 记录详细错误信息
                        import traceback
                        error_detail = traceback.format_exc()
                        console.print(f"[red]错误堆栈:\n{error_detail}[/red]")
                        
                        stats["failed"] += 1
                        failed_configs.append((display_name, group_item, error_msg))
                        progress.update(
                            task,
                            advance=1,
                            description=f"下载失败: {data_id_item}"
                        )
        
        except Exception as e:
            console.print(f"[red]下载过程出错: {e}[/red]")
            import traceback
            console.print(f"[red]错误堆栈:\n{traceback.format_exc()}[/red]")
            return stats
        
        if failed_configs:
            console.print("\n[red]下载失败的配置:[/red]")
            for data_id_item, group_item, error in failed_configs:
                console.print(f"  [red]{data_id_item} (group: {group_item})[/red]: {error}")
        
        return stats


def load_config_from_env() -> Dict:
    """从环境变量加载Nacos配置"""
    config = {}
    
    # 服务器地址（必需）
    config["server_addresses"] = os.environ.get("NACOS_SERVER_ADDRESSES")
    if not config["server_addresses"]:
        # 尝试从单独的host和port获取
        host = os.environ.get("NACOS_SERVER_HOST", "localhost")
        port = os.environ.get("NACOS_SERVER_PORT", "8848")
        config["server_addresses"] = f"{host}:{port}"
    
    # 用户名和密码（可选）
    config["username"] = os.environ.get("NACOS_USERNAME")
    config["password"] = os.environ.get("NACOS_PASSWORD")
    
    # 命名空间（可选）
    config["namespace"] = os.environ.get("NACOS_NAMESPACE")
    
    return config


async def _upload_async(
    config_dir: str,
    server_addresses: Optional[str],
    username: Optional[str],
    password: Optional[str],
    namespace: Optional[str],
    group: Optional[str],
    recursive: bool,
    overwrite: bool,
    incremental: bool,
    use_folder_as_group: bool,
):
    """异步上传函数"""
    # 加载配置
    env_config = load_config_from_env()
    
    # 使用命令行参数覆盖环境变量
    server_addresses = server_addresses or env_config["server_addresses"]
    username = username or env_config.get("username")
    password = password or env_config.get("password")
    namespace = namespace or env_config.get("namespace")
    
    if not server_addresses:
        console.print("[red]错误: 必须指定Nacos服务器地址（通过--server参数或NACOS_SERVER_ADDRESSES环境变量）[/red]")
        raise typer.Exit(1)
    
    try:
        manager = NacosConfigManager(
            server_addresses=server_addresses,
            username=username,
            password=password,
            namespace=namespace,
        )
        
        console.print(f"[cyan]开始上传配置...[/cyan]")
        console.print(f"  服务器: {server_addresses}")
        console.print(f"  命名空间: {namespace or '(默认)'}")
        console.print(f"  配置目录: {config_dir}")
        console.print(f"  组名: {group or Path(config_dir).name}")
        console.print()
        
        stats = await manager.upload_configs(
            config_dir=Path(config_dir),
            group=group,
            namespace=namespace,
            recursive=recursive,
            overwrite=overwrite,
            incremental=incremental,
            use_folder_as_group=use_folder_as_group,
        )
        
        console.print()
        console.print("[green]上传完成！[/green]")
        table = Table(title="上传统计")
        table.add_column("状态", style="cyan")
        table.add_column("数量", style="magenta")
        table.add_row("成功", str(stats["success"]))
        table.add_row("失败", str(stats["failed"]))
        table.add_row("跳过", str(stats["skipped"]))
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]上传失败: {e}[/red]")
        import traceback
        console.print(f"[red]错误堆栈:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


async def _download_async(
    output_dir: str,
    server_addresses: Optional[str],
    username: Optional[str],
    password: Optional[str],
    namespace: Optional[str],
    group: Optional[str],
    data_id: Optional[str],
    overwrite: bool,
):
    """异步下载函数"""
    # 加载配置
    env_config = load_config_from_env()
    
    # 使用命令行参数覆盖环境变量
    server_addresses = server_addresses or env_config["server_addresses"]
    username = username or env_config.get("username")
    password = password or env_config.get("password")
    namespace = namespace or env_config.get("namespace")
    
    if not server_addresses:
        console.print("[red]错误: 必须指定Nacos服务器地址（通过--server参数或NACOS_SERVER_ADDRESSES环境变量）[/red]")
        raise typer.Exit(1)
    
    try:
        manager = NacosConfigManager(
            server_addresses=server_addresses,
            username=username,
            password=password,
            namespace=namespace,
        )
        
        console.print(f"[cyan]开始下载配置...[/cyan]")
        console.print(f"  服务器: {server_addresses}")
        console.print(f"  命名空间: {namespace or '(默认)'}")
        console.print(f"  输出目录: {output_dir}")
        if group:
            console.print(f"  组名: {group}")
        if data_id:
            console.print(f"  配置ID: {data_id}")
        console.print()
        
        stats = await manager.download_configs(
            output_dir=Path(output_dir),
            group=group,
            namespace=namespace,
            data_id=data_id,
            overwrite=overwrite,
        )
        
        console.print()
        console.print("[green]下载完成！[/green]")
        table = Table(title="下载统计")
        table.add_column("状态", style="cyan")
        table.add_column("数量", style="magenta")
        table.add_row("成功", str(stats["success"]))
        table.add_row("失败", str(stats["failed"]))
        table.add_row("跳过", str(stats["skipped"]))
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]下载失败: {e}[/red]")
        import traceback
        console.print(f"[red]错误堆栈:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command("upload")
def upload_command(
    config_dir: str = typer.Argument(..., help="配置文件目录路径"),
    server_addresses: Optional[str] = typer.Option(None, "--server", "-s", help="Nacos服务器地址，格式: ip:port 或 ip1:port1,ip2:port2"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Nacos用户名"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Nacos密码"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="命名空间ID"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="配置组名"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r", help="是否递归遍历子目录"),
    overwrite: bool = typer.Option(False, "--overwrite/--no-overwrite", "-o", help="是否覆盖已存在的配置"),
    incremental: bool = typer.Option(False, "--incremental/--no-incremental", "-i", help="是否增量上传（只上传不存在的配置）"),
    use_folder_as_group: bool = typer.Option(False, "--use-folder-as-group/--no-use-folder-as-group", help="是否使用子目录名作为group（默认使用顶层目录名）"),
):
    """上传配置文件到Nacos"""
    asyncio.run(_upload_async(
        config_dir=config_dir,
        server_addresses=server_addresses,
        username=username,
        password=password,
        namespace=namespace,
        group=group,
        recursive=recursive,
        overwrite=overwrite,
        incremental=incremental,
        use_folder_as_group=use_folder_as_group,
    ))


@app.command("download")
def download_command(
    output_dir: str = typer.Argument(..., help="输出目录路径"),
    server_addresses: Optional[str] = typer.Option(None, "--server", "-s", help="Nacos服务器地址，格式: ip:port 或 ip1:port1,ip2:port2"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Nacos用户名"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Nacos密码"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="命名空间ID"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="配置组名（不指定则下载所有group）"),
    data_id: Optional[str] = typer.Option(None, "--data-id", "-d", help="配置ID（不指定则下载指定group的所有配置）"),
    overwrite: bool = typer.Option(False, "--overwrite/--no-overwrite", "-o", help="是否覆盖已存在的文件"),
):
    """从Nacos下载配置文件"""
    asyncio.run(_download_async(
        output_dir=output_dir,
        server_addresses=server_addresses,
        username=username,
        password=password,
        namespace=namespace,
        group=group,
        data_id=data_id,
        overwrite=overwrite,
    ))


if __name__ == "__main__":
    app()
