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
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger("cf_optimizer")
        self.binary_name = "CloudflareST.exe" if os.name == 'nt' else "CloudflareST"
        self.binary_path = self.data_dir / self.binary_name
        self._init_ip_files()
    
    def _init_ip_files(self):
        """初始化IP范围文件"""
        # IPv4
        ipv4_file = self.data_dir / "ip.txt"
        if not ipv4_file.exists():
            with open(ipv4_file, "w") as f:
                f.write("\n".join([
                    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22",
                    "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
                    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22",
                    "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
                    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22"
                ]))
        
        # IPv6
        ipv6_file = self.data_dir / "ipv6.txt"
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
        
        # 添加字符串参数
        str_params = ['url', 'httping_code', 'cfcolo', 'f', 'ip', 'o']
        for param in str_params:
            if param in args and args[param]:
                cmd.extend([f"-{param}", str(args[param])])
        
        # 添加布尔参数
        bool_params = {
            'httping': '-httping',
            'dd': '-dd',
            'allip': '-allip',
            'debug': '-debug'
        }
        for param, flag in bool_params.items():
            if param in args and args[param]:
                cmd.append(flag)
        
        # 添加IP类型
        if args.get('ipv4'):
            cmd.extend(["-f", str(self.data_dir / "ip.txt")])
        if args.get('ipv6'):
            cmd.extend(["-f", str(self.data_dir / "ipv6.txt")])
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        # 执行命令
        try:
            process = subprocess.Popen(
               cmd,
                cwd=self.data_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 实时输出日志
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output_lines.append(line.strip())
                    self.logger.info(line.strip())
            
            # 检查进程退出状态
            if process.returncode != 0:
                error_msg = f"CloudflareST exited with code {process.returncode}: {' '.join(process.stderr.readlines())}"
                self.logger.error(error_msg)
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr=error_msg)

            # 获取结果文件路径
            result_file = Path(args.get('o', 'data/result.csv'))
            
            # 记录最优IP
            self.log_best_ip(result_file)
            
            return result_file

        except subprocess.CalledProcessError as e:
            self.logger.error(f"CloudflareST execution failed: {e}")
        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            return None

    def get_results(self):
        """获取优选结果"""
        try:
            result_file = Path(config.get('cloudflare', 'o', fallback='data/result.csv'))
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
                
                # 专门记录最优IP到日志文件
                log_dir = Path(__file__).parent.parent / "log"
                log_dir.mkdir(exist_ok=True, parents=True)
                log_file = log_dir / "cf.log"
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file, "a") as lf:
                    lf.write(f"[{timestamp}] [INFO] [cf_optimizer] - {log_msg}\n")
        except Exception as e:
            self.logger.error(f"记录最优IP时出错: {str(e)}")