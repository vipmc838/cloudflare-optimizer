import os
import subprocess
import logging
import requests
import zipfile
import tarfile
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
            
            # 根据系统确定下载文件
            system = os.name
            arch = "amd64"
            
            if system == "nt":  # Windows
                filename = f"CloudflareST_windows_{arch}.zip"
            elif system == "posix":  # Linux/Mac
                if os.uname().sysname == "Darwin":
                    filename = f"CloudflareST_darwin_{arch}.zip"
                else:
                    filename = f"CloudflareST_linux_{arch}.tar.gz"
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
            if system != "nt":
                os.chmod(self.binary_path, 0o755)
            
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
        
        # 构建命令
        cmd = [str(self.binary_path)]
        
        # 添加数值参数
        num_params = ['n', 't', 'dn', 'dt', 'tp', 'p', 'tl', 'tll', 'sl']
        for param in num_params:
            if param in args:
                cmd.extend([f"-{param}", str(args[param])])
        
        # 添加浮点参数
        float_params = ['tlr']
        for param in float_params:
            if param in args:
                cmd.extend([f"-{param}", str(args[param])])
        
        # 添加其他字符串参数 (文件路径参数将单独处理)
        str_params = ['url', 'httping_code', 'cfcolo', 'ip']
        for param in str_params:
            if param in args and args[param]:
                cmd.extend([f"-{param}", str(args[param])])
        
        # 添加布尔参数
        bool_params = {'httping': '-httping', 'dd': '-dd', 'allip': '-allip', 'debug': '-debug'}
        for param, flag in bool_params.items():
            if param in args and args[param]:
                cmd.append(flag)
        
        # 显式处理输入文件 -f (使用绝对路径)
        # CloudflareST 支持多个 -f 参数
        ipv4_file = config.get('paths', 'ipv4_file')
        ipv6_file = config.get('paths', 'ipv6_file')
        if args.get('ipv4'):
            cmd.extend(["-f", ipv4_file])
        if args.get('ipv6'):
            cmd.extend(["-f", ipv6_file])
        
        # 显式处理输出文件 -o (使用绝对路径)
        result_file = Path(args.get('o', config.get('paths', 'result_file')))
        cmd.extend(["-o", str(result_file)])
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        # 执行命令
        try:
            # 使用 subprocess.run 等待命令完成并捕获输出
            process = subprocess.run(
                cmd,
                cwd=self.data_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            # 记录 CloudflareST 的标准输出和错误输出
            if process.stdout:
                for line in process.stdout.strip().split('\n'):
                    self.logger.info(line)
            if process.stderr:
                self.logger.warning("CloudflareST stderr:")
                for line in process.stderr.strip().split('\n'):
                    self.logger.warning(line)
            
            # 记录最优IP
            self.log_best_ip(result_file)
            
            return result_file
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            return None

    def get_results(self):
        """获取优选结果"""
        try:
            result_file = Path(config.get('cloudflare', 'o', fallback=config.get('paths', 'result_file')))
            if not result_file.exists():
                return None
            
            results = []
            with open(result_file, "r") as f:
                headers = f.readline().strip().split(',')
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
            with open(result_file, "r") as f:
                # 跳过标题行
                f.readline()
                best_line = f.readline()
                if not best_line:
                    self.logger.warning("结果文件为空，无法记录最优IP")
                    return
                
                # 解析最优IP信息
                parts = best_line.strip().split(',')
                if len(parts) < 6:
                    self.logger.warning(f"结果行格式错误: {best_line}")
                    return
                
                ip = parts[0]
                latency = parts[1]
                jitter = parts[2]
                loss = parts[3]
                speed = parts[4] if len(parts) > 4 else "N/A"
                
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
