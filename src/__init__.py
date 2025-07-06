"""
Cloudflare IP 优选服务 - 核心模块

此包包含 Cloudflare IP 优选服务的所有核心功能：
- config_loader: 配置加载和管理
- cf_optimizer: Cloudflare IP 优选核心逻辑
- scheduler: 定时任务调度
- api_server: API 服务接口
"""

# 简化导入路径
from .config_loader import config
from .cf_optimizer import CloudflareOptimizer
from .scheduler import TaskScheduler
from .api_server import app

# 定义 __all__ 变量，控制 from src import * 的行为
__all__ = [
    'config',
    'CloudflareOptimizer',
    'TaskScheduler',
    'app'
]

# 包版本信息
__version__ = "1.0.0"
__author__ = "my railgun"
__email__ = "your.email@example.com"

# 包初始化代码（可选）
print(f"Initializing Cloudflare IP Optimizer package v{__version__}")