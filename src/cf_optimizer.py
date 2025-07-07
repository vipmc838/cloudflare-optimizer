import os
import subprocess
import logging
import requests
import zipfile
import tarfile
import platform
from pathlib import Path
from datetime import datetime
from .config_loader import config

class CloudflareOptimizer:
    def __init__(self):
        # 从配置中获取路径
        self.data_dir = Path(config.get('paths', 'data_dir'))
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger("cf_optimizer")
        
        # 在非Windows系统（如Docker容器）中，使用配置的路径；Windows下则附加.exe
        binary_path_str = config.get('paths', 'binary_file')
        if os.name == 'nt' and not binary_path_str.endswith('.exe'):
            binary_path_str += '.exe'
        self.binary_path = Path(binary_path_str)

        self._init_ip_files()
    
    def _init_ip_files(self):
        """初始化IP范围文件"""
        ipv4_file = Path(config.get('paths', 'ipv4_file'))
        if not ipv4_file.exists():
            with open(ipv4_file, "w") as f:
                f.write("\n".join([
                    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
                    "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
                    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
                    "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
                    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22"
                ]))
        
        ipv6_file = Path(config.get('paths', 'ipv6_file'))
        if not ipv6_file.exists():
            with open(ipv6_file, "w") as f:
                f.write("\n".join([
                    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32",
                    "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29",
                    "2c0f:f248::/32"
                ]))

    def _download_cloudflarest(self):
        """下载CloudflareSpeedTest工具"""
        try:
            # 获取最新版本
            url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
            response = requests.get(url)
            data = response.json()
            version = data["tag_name"]
            
            # 根据系统和架构确定下载文件
            system = platform.system().lower()
            machine = platform.machine().lower()
            if 'aarch64' in machine or 'arm64' in machine:
                arch = "arm64"
            elif 'arm' in machine: # 涵盖 armv7l 等
                arch = "armv7"
            elif 'x86_64' in machine or 'amd64' in machine:
                arch = "amd64"
            else:
                self.logger.error(f"不支持的系统架构: {machine}")
                return False
            
            if system == "windows":
                filename = f"CloudflareST_windows_{arch}.zip"
            elif system == "linux":
                filename = f"CloudflareST_linux_{arch}.tar.gz"
            elif system == "darwin":
                filename = f"CloudflareST_darwin_{arch}.zip"
            else:
                self.logger.error("Unsupported OS")
                return False
            
            download_url = f"https://github.com/XIU2/CloudflareSpeedTest/releases/download/{version}/{filename}"
            local_path = self.data_dir / filename
            
            # 下载文件
            self.logger.info(f"Downloading CloudflareST: {download_url}")
            proxy_url = config.get('cloudflare', 'proxy')
            proxies = {"https": proxy_url} if proxy_url else None
            response = requests.get(download_url, proxies=proxies, stream=True)
            
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 解压文件
            if filename.endswith(".zip"):
                with zipfile.ZipFile(local_path, "r") as zip_ref:
                    zip_ref.extractall(self.data_dir)
            else:  # .tar.gz
                with tarfile.open(local_path, "r:gz") as tar_ref:
                    tar_ref.extractall(self.data_dir)
            
            # 设置执行权限 (Unix)
            if system != "windows":
                os.chmod(self.binary_path, 0o755)
            
            # 清理下载和解压后的多余文件
            self.logger.info("清理下载文件...")
            try:
                # 1. 删除下载的压缩包
                os.remove(local_path)
                self.logger.info(f"已删除压缩包: {local_path}")
                # 2. 删除其他不必要的文件
                for extra_file in ["cfst_hosts.sh", "使用+错误+反馈说明.txt"]:
                    file_to_delete = self.data_dir / extra_file
                    if file_to_delete.exists():
                        os.remove(file_to_delete)
                        self.logger.info(f"已删除附加文件: {file_to_delete}")
            except OSError as e:
                self.logger.warning(f"清理文件时出错: {e}")

            return True
        except Exception as e:
            self.logger.error(f"Download failed: {str(e)}")
            return False

    def run_optimization(self):
        """执行Cloudflare IP优选"""
        # 检查并安装工具
        if not self.binary_path.exists():
            if not self._download_cloudflarest():
                self.logger.error("CloudflareST not found and download failed")
                return None
        
        # 获取配置参数
        args = config.get_args_dict()
        
        # 定义参数类型映射
        param_map = {
            # 参数名: (类型, 是否需要值)
            'n': 'value', 't': 'value', 'dn': 'value', 'dt': 'value', 'tp': 'value',
            'p': 'value', 'tl': 'value', 'tll': 'value', 'sl': 'value', 'tlr': 'value',
            'url': 'value', 'httping_code': 'value', 'cfcolo': 'value', 'ip': 'value',
            'httping': 'flag', 'dd': 'flag', 'allip': 'flag', 'debug': 'flag'
        }

        cmd = [str(self.binary_path)]
        for key, value in args.items():
            if key in param_map:
                param_type = param_map[key]
                if param_type == 'value' and value:
                    cmd.extend([f"-{key}", str(value)])
                elif param_type == 'flag' and value:
                    cmd.append(f"-{key}")
        
        # 显式处理输入文件 -f (使用绝对路径)
        # CloudflareST 支持多个 -f 参数
        ipv4_file = config.get('paths', 'ipv4_file')
        ipv6_file = config.get('paths', 'ipv6_file')
        if args.get('ipv4'):
            cmd.extend(["-f", ipv4_file])
        if args.get('ipv6'):
            cmd.extend(["-f", ipv6_file])
        
        # 显式处理输出文件 -o (使用绝对路径)
        result_file = Path(args.get('o', config.get('paths', 'result_file')))  # 确保正确使用了配置中的 result_file
        cmd.extend(["-o"， 'str(result_file)'])
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        # 执行命令
        try:
            # 使用 Popen 实时捕获和打印输出，确保日志逐步生成
            process = subprocess.Popen(
                cmd,
                cwd=self.data_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1  # 行缓冲
            )

            # 实时读取标准输出并记录
            if process.stdout:  # 确保 process.stdout 不为 None
                for line in iter(process.stdout.readline, ''):
                    # 移除行尾的换行符并记录，这样每条日志都会有自己的时间戳
                    self.logger.info(line.strip())
                process.stdout.close()

            # 等待进程结束
            return_code = process.wait()
            self.logger.info(f"CloudflareST exited with code: {return_code}")  # 记录退出代码

            # 读取可能存在的标准错误输出
            if process.stderr:  # 确保 process.stderr 不为 None
                stderr_output = process.stderr.read()
                if stderr_output:
                    self.logger.warning("CloudflareST stderr:")
                    for line in stderr_output.strip().split('\n'):
                        self.logger.warning(line)
                process.stderr.close()
            else:
                self.logger.info("CloudflareST stderr: <empty>")  # 如果 stderr 为空，记录信息

            if return_code != 0:
                error_message = f"CloudflareST failed (exit code: {return_code}). Check logs above for details."
                self.logger.error(error_message)
                # 抛出异常，让调用者也能感知到错误
                raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr_output)

            # 记录最优IP
            self.log_best_ip(result_file)
            
            return result_file
        except FileNotFoundError:
            self.logger.error(f"命令执行失败: 未找到 CloudflareST 工具 at '{self.binary_path}'. 请检查路径或重新安装。")
            return None
        except subprocess.CalledProcessError as e:
            # 捕获子进程异常，记录更详细的错误信息
            self.logger.error(f"CloudflareST execution error: {e}")
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            return None

    def get_results(self):
        """获取优选结果"""
        try:
            result_file = Path(config.get('cloudflare', 'o', fallback=config.get('paths', 'result_file')))
            if not result_file.exists():
                return None
            
            # 定义一个从中文到英文的映射，并移除空格，使键更健壮
            header_map = {
                "IP 地址": "ip",
                "已发送": "sent",
                "已接收": "received",
                "丢包率": "loss_rate",
                "平均延迟": "avg_latency",
                "延迟抖动": "jitter",
                "下载速度": "download_speed",
                "TCP 协议": "tcp_protocol",
                "HTTP 协议": "http_protocol",
                "TLS 协议": "tls_protocol",
                "文件 URL": "file_url",
                "地区": "location",
                "组织": "organization"
            }

            results = []
            with open(result_file, "r", encoding='utf-8') as f:
                raw_headers = f.readline().strip().split(',')
                # 清理并映射表头，对于未知表头，移除空格并转为小写
                headers = [header_map.get(h.strip(), h.strip().replace(" ", "_").lower()) for h in raw_headers]
                for line in f:
                    values = line.strip().split(',')
                    if len(values) < len(headers):
                        continue
                    result = {headers[i]: values[i] for i in range(len(headers))}
                    results.append(result)
            return results
        except Exception as e:
            self.logger.error(f"Failed to read results: {str(e)}")
            return None

    def log_best_ip(self, result_file: Path):
        """记录最优IP到日志文件"""
        if not result_file.exists():
            self.logger.warning("结果文件不存在，无法记录最优IP")
            return
        
        try:
            with open(result_file, "r", encoding='utf-8') as f:
                headers = [h.strip() for h in f.readline().strip().split(',')]
                best_line = f.readline()
                if not best_line:
                    self.logger.warning("优选结果为空（result.csv 文件没有有效数据），请检查 CloudflareST 工具的输出和配置参数。")
                    return
                
                values = best_line.strip().split(',')
                if len(values) < len(headers):
                    self.logger.warning(f"结果行格式错误: {best_line}")
                    return
                
                result_dict = dict(zip(headers, values))
                ip = result_dict.get("IP 地址", "N/A")
                latency = result_dict.get("平均延迟", "N/A")
                jitter = result_dict.get("延迟抖动", "N/A")
                loss = result_dict.get("丢包率", "N/A")
                speed = result_dict.get("下载速度", "N/A")
                
                # 记录到日志
                log_msg = (
                    f"优选完成! 最优IP: {ip}, "
                    f"延迟: {latency}ms, "
                    f"抖动: {jitter}ms, "
                    f"丢包率: {loss}%, "
                    f"下载速度: {speed}MB/s"
                )
                self.logger.info(log_msg)
        except Exception as e:
            self.logger.error(f"记录最优IP时出错: {str(e)}")
