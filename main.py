import logging
import threading
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import os
import uvicorn

from src.config_loader import config
from src.scheduler import TaskScheduler
from src.api_server import app

def setup_logging():
    """配置日志系统，确保日志文件可写"""
    # 从配置中读取日志文件路径
    # 这是配置日志文件的唯一真实来源
    log_file_path = config.get('paths', 'log_file', fallback='/app/log/cf.log')
    log_file = Path(log_file_path)
    log_dir = log_file.parent
    
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 总是先配置控制台处理器，以便能看到所有启动和错误信息
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 尝试配置日志文件处理器，并进行详细的权限检查
    try:
        # 步骤 1: 确保日志目录存在。如果创建失败，会抛出异常。
        logger.info(f"检查日志目录: {log_dir}")
        log_dir.mkdir(exist_ok=True, parents=True)
        
        # 步骤 2: 显式地创建日志文件（如果不存在）。
        # 这有助于在配置处理器之前就发现权限问题。
        if not log_file.exists():
            logger.info(f"日志文件 '{log_file}' 不存在，正在创建...")
            log_file.touch()
        else:
            logger.info(f"日志文件 '{log_file}' 已存在。")
            
        # 步骤 3: 检查文件是否真正可写。
        if not os.access(log_file, os.W_OK):
            # 如果不可写，抛出明确的权限错误。
            raise PermissionError(f"日志文件 '{log_file}' 不可写，请检查文件权限。")
        
        logger.info(f"日志文件 '{log_file}' 权限检查通过。")

        # 步骤 4: 配置 TimedRotatingFileHandler
        # 使用 utf-8 编码以避免乱码问题
        file_handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=7, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"日志文件处理器配置成功，日志将写入: {log_file}")
    except Exception as e:
        # 如果文件处理器创建失败，在控制台记录一个明确的错误，这对于诊断Docker权限问题至关重要
        logger.error(f"无法配置日志文件处理器 at '{log_file}'. 请检查路径和容器权限。错误: {e}")
    
    # 记录启动信息
    logger.info("=" * 60)
    logger.info("Cloudflare IP Optimizer 服务启动")
    logger.info("=" * 60)

def start_api_server():
    """启动API服务器"""
    port = config.getint('cloudflare', 'api_port', fallback=6788)
    logger = logging.getLogger("main")
    logger.info(f"Starting API server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    # 配置日志
    setup_logging()
    logger = logging.getLogger("main")
    
    logger.info("Starting Cloudflare IP Optimizer")
    
    # 根据配置创建所需目录
    data_dir = Path(config.get('paths', 'data_dir', fallback='/app/data'))
    log_dir = Path(config.get('paths', 'log_dir', fallback='/app/log'))
    data_dir.mkdir(exist_ok=True, parents=True)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    try:
        # 启动调度器
        scheduler = TaskScheduler()
        scheduler_thread = threading.Thread(target=scheduler.start)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # 启动API服务器
        start_api_server()
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        raise
