import logging
import threading
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import uvicorn

from src.config_loader import config
from src.scheduler import TaskScheduler
from src.api_server import app

def setup_logging():
    """配置日志系统"""
    # 创建日志目录
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = log_dir / "cf.log"
    
    # 创建根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建文件处理器（每天轮转，保留7天）
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=7
    )
    file_handler.setLevel(logging.INFO)
    
    # 创建日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
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
    
    # 确保目录存在
    Path("data").mkdir(exist_ok=True, parents=True)
    Path("log").mkdir(exist_ok=True, parents=True)
    
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