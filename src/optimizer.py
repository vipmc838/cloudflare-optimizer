# d:\桌面\cloudflare-ip-optimizer-main\src\optimizer.py
import os
import sys
import platform
import requests
import zipfile
import tarfile
import subprocess
import logging
import csv
from io import StringIO
from .state import app_state
from .updater import update_openwrt_hosts

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CloudflareOptimizer:
    def __init__(self, config, config_dir='.'):
        self.config_dir = config_dir
        self.tool_dir = os.path.join(self.config_dir, "cfs_tool")
        self.tool_path = self._get_tool_path()
        self.params = config['CloudflareSpeedTest']['params'].split()
        self.openwrt_config = config['OpenWRT'] if 'OpenWRT' in config else None
        
        # 获取原始输出文件名并构建完整路径
        output_filename = self._find_output_filename()
        self.output_filepath = os.path.join(self.config_dir, output_filename)
        self._update_output_param_with_full_path()

    def _update_output_param_with_full_path(self):
        """将参数中的相对输出文件名替换为完整路径，以确保文件在正确的位置生成。"""
        try:
            index = self.params.index('-o') if '-o' in self.params else self.params.index('--output')
            self.params[index + 1] = self.output_filepath
        except (ValueError, IndexError):
            pass # 此错误已在 _find_output_filename 中处理
        
    def _find_output_filename(self):
        """从参数中解析输出文件名"""
        try:
            # 查找 -o 或 --output 参数
            index = self.params.index('-o') if '-o' in self.params else self.params.index('--output')
            return self.params[index + 1]
        except (ValueError, IndexError):
            logging.error("配置文件中的 params 必须包含 '-o <filename>' 参数来指定输出文件。")
            sys.exit(1)

    def _get_tool_path(self):
        """根据操作系统和架构确定工具的完整路径"""
        os_name = sys.platform
        arch = platform.machine().lower()
        
        filename = "CloudflareST"
        if os_name == "win32":
            filename += ".exe"
            
        return os.path.join(self.tool_dir, filename)

    def _get_download_url(self):
        """根据操作系统和架构构建下载URL"""
        os_map = {
            "linux": "linux",
            "darwin": "darwin",
            "win32": "windows"
        }
        arch_map = {
            "amd64": "amd64",
            "x86_64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64"
        }
        
        os_name = os_map.get(sys.platform)
        arch = arch_map.get(platform.machine().lower())

        if not os_name or not arch:
            raise RuntimeError(f"不支持的操作系统或架构: {sys.platform} / {platform.machine()}")

        # 从 GitHub API 获取最新的 release 信息
        try:
            api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            # 查找匹配的 asset
            asset_name_fragment = f"CloudflareST_{os_name}_{arch}"
            for asset in release_data.get("assets", []):
                if asset_name_fragment in asset.get("name", ""):
                    logging.info(f"找到匹配的下载资源: {asset['name']}")
                    return asset["browser_download_url"]
        except requests.RequestException as e:
            logging.error(f"无法从 GitHub API 获取最新版本信息: {e}")
        
        raise RuntimeError("无法找到适用于当前系统的 CloudflareSpeedTest 下载链接。")


    def download_and_extract_tool(self):
        """如果工具不存在，则下载并解压"""
        if os.path.exists(self.tool_path):
            logging.info(f"CloudflareSpeedTest 工具已存在于: {self.tool_path}")
            return

        logging.info("CloudflareSpeedTest 工具未找到，开始下载...")
        os.makedirs(self.tool_dir, exist_ok=True)
        
        try:
            url = self._get_download_url()
            archive_filename = url.split('/')[-1]
            archive_path = os.path.join(self.tool_dir, archive_filename)

            # 下载
            with requests.get(url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(archive_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logging.info("下载完成，开始解压...")
            
            # 解压
            if archive_filename.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.tool_dir)
            elif archive_filename.endswith(('.tar.gz', '.tgz')):
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(self.tool_dir)
            else:
                raise ValueError(f"不支持的压缩文件格式: {archive_filename}")
            
            # 清理压缩包
            os.remove(archive_path)
            
            # 添加执行权限 (Linux/macOS)
            if sys.platform != "win32":
                os.chmod(self.tool_path, 0o755)

            logging.info(f"工具成功解压到: {self.tool_path}")

        except Exception as e:
            logging.error(f"下载或解压工具时出错: {e}")
            sys.exit(1)

    def run_speed_test(self):
        """执行优选IP任务"""
        if not app_state.optimizer_lock.acquire(blocking=False):
            logging.warning("优选任务已在运行中，本次触发被跳过。")
            return

        try:
            logging.info("开始执行 Cloudflare IP 优选...")
            command = [self.tool_path] + self.params
            
            # 确保结果文件被清理，以免读取到旧数据
            if os.path.exists(self.output_filepath):
                os.remove(self.output_filepath)

            # 设置 cwd (current working directory) 为工具所在的目录
            # 这可以确保工具生成的所有临时文件（如 ip.txt）都在正确的路径下
            process = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8', cwd=self.tool_dir)

            if process.returncode != 0:
                logging.error(f"CloudflareSpeedTest 执行失败，错误信息:\n{process.stderr}")
                return

            logging.info("IP 优选完成，开始解析结果...")
            self._parse_results()

        except Exception as e:
            logging.error(f"执行优选任务时发生未知错误: {e}")
        finally:
            app_state.optimizer_lock.release()

    def _parse_results(self):
        """解析CSV结果文件并更新全局状态"""
        try:
            with open(self.output_filepath, 'r', encoding='utf-8-sig') as f:
                # 使用 StringIO 来处理内存中的数据，方便 csv 模块读取
                content = f.read()
                csv_file = StringIO(content)
                reader = csv.DictReader(csv_file)
                results = list(reader)

                if not results:
                    logging.warning("优选结果为空，未找到可用IP。")
                    app_state.best_ip = None
                    app_state.last_results = []
                    return

                # 第一行数据通常是最佳IP
                best_result = results[0]
                app_state.best_ip = best_result.get('IP 地址')
                app_state.last_results = results

                logging.info(f"成功解析结果，最优IP: {app_state.best_ip}")

                # 如果启用了 OpenWRT 更新，则执行更新
                if self.openwrt_config and app_state.best_ip:
                    update_openwrt_hosts(self.openwrt_config, app_state.best_ip)
                
        except FileNotFoundError:
            logging.error(f"结果文件 '{self.output_filepath}' 未找到，解析失败。")
        except Exception as e:
            logging.error(f"解析结果时出错: {e}")
