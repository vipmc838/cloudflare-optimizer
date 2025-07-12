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
from .updater import update_openwrt_hosts, update_adguard_hosts

class CloudflareOptimizer:
    def __init__(self, config, config_dir='.'):
        self.config = config # 保存对配置对象的引用
        self.config_dir = config_dir
        self.tool_dir = os.path.join(self.config_dir, "cfst_tool")
        self.tool_path = self._get_tool_path()
        self.reload_config() # 调用新方法来加载参数

    def reload_config(self):
        """从 self.config 对象重新加载配置参数，以便热更新。"""
        logging.info("正在重新加载 Optimizer 配置...")
        self.params = self.config['cfst']['params'].split()
        self.openwrt_config = self.config['OpenWRT'] if 'OpenWRT' in self.config else None
        self.download_config = self.config['Download'] if 'Download' in self.config else {}
        
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
        
        filename = "cfst"
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
        # 扩展架构映射以支持更多平台，如 32 位和旧版 ARM
        arch_map = {
            "amd64": "amd64",
            "x86_64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
            "i386": "386",
            "i686": "386",
            "x86": "386",
            "armv7l": "armv7",
            "armv6l": "armv6",
            "mips": "mips",
            "mipsle": "mipsle",
            "mips64": "mips64",
            "mips64le": "mips64le",
        }
        
        system_platform = sys.platform
        system_machine = platform.machine().lower()
        
        os_name = os_map.get(system_platform)
        arch = arch_map.get(system_machine)

        # 增加详细日志，方便调试
        logging.info(f"系统检测: platform='{system_platform}', machine='{system_machine}'")
        logging.info(f"映射结果: os_name='{os_name}', arch='{arch}'")

        if not os_name or not arch:
            logging.error(f"无法映射当前系统。os_map 支持: {list(os_map.keys())}, arch_map 支持: {list(arch_map.keys())}")
            raise RuntimeError(f"不支持的操作系统或架构: {system_platform} / {system_machine}")

        # 从 GitHub API 获取最新的 release 信息
        try:
            api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
            logging.info(f"正在从 GitHub API 获取最新版本信息: {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            # 按照您的要求，打印出从 API 获取到的所有可用资源文件名
            available_assets = [asset.get("name", "unnamed_asset") for asset in release_data.get("assets", [])]
            logging.info(f"从 API 获取到以下可用资源: {available_assets}")

            # 查找匹配的 asset
            asset_name_fragment = f"cfst_{os_name}_{arch}"
            logging.info(f"正在查找包含 '{asset_name_fragment}' 的资源文件...")
            
            for asset in release_data.get("assets", []):
                asset_name = asset.get("name", "")
                if asset_name_fragment in asset_name:
                    logging.info(f"找到匹配的下载资源: {asset['name']}")
                    return asset["browser_download_url"]
        except requests.RequestException as e:
            logging.error(f"无法从 GitHub API 获取最新版本信息: {e}")
        
        # 抛出更详细的错误信息
        error_message = "无法找到适用于当前系统的 CloudflareSpeedTest 下载链接。"
        if 'available_assets' in locals() and available_assets:
            error_message += f" 期望文件名包含 '{asset_name_fragment}'，但只找到了: {available_assets}"
        raise RuntimeError(error_message)


    def download_and_extract_tool(self):
        """如果工具不存在，则下载并解压"""
        if os.path.exists(self.tool_path):
            logging.info(f"cfst 工具已存在于: {self.tool_path}")
            return

        logging.info("cfst 工具未找到，开始下载...")
        os.makedirs(self.tool_dir, exist_ok=True)
        
        try:
            url = self._get_download_url()

            proxy_url = self.download_config.get('proxy', '').strip()
            if proxy_url:
                download_url = proxy_url + url
                logging.info(f"将通过代理下载: {download_url}")
            else:
                download_url = url
                logging.info(f"开始直接下载: {url}")

            archive_filename = url.split('/')[-1]
            archive_path = os.path.join(self.tool_dir, archive_filename)

            # 下载
            with requests.get(download_url, stream=True, timeout=60) as r:
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
            
            # 设置 cwd (current working directory) 为工具所在的目录
            # 这可以确保工具生成的所有临时文件（如 ip.txt）都在正确的路径下
            process = subprocess.run(
                command, capture_output=True, text=True, encoding='utf-8', cwd=self.tool_dir)

            if process.returncode != 0:
                logging.error(f"cfst 执行失败，错误信息:\n{process.stderr}")
                return

            logging.info("IP 优选完成，开始解析结果...")
            self._parse_results()

        except Exception as e:
            logging.error(f"执行优选任务时发生未知错误: {e}")
        finally:
            app_state.optimizer_lock.release()

    def load_results_from_file(self):
        """从现有的结果文件中加载数据到应用状态"""
        if os.path.exists(self.output_filepath):
            logging.info(f"正在从 {self.output_filepath} 加载已有结果...")
            self._parse_results()
        else:
            logging.warning(f"结果文件 {self.output_filepath} 不存在，跳过加载。")


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
                if self.openwrt_config and self.openwrt_config.getboolean('enabled') and app_state.best_ip:
                    target = self.openwrt_config.get('target', fallback='openwrt')
                    if target == 'adguardhome':
                        update_adguard_hosts(self.openwrt_config, app_state.best_ip)
                    else: # 'openwrt' or 'mosdns'
                        update_openwrt_hosts(self.openwrt_config, app_state.best_ip)
                
        except FileNotFoundError:
            logging.error(f"结果文件 '{self.output_filepath}' 未找到，解析失败。")
        except Exception as e:
            logging.error(f"解析结果时出错: {e}")
