# d:\桌面\cloudflare-ip-optimizer-main\src\main.py
import configparser
from typing import Any
import logging
import os
import sys
import threading
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from waitress import serve
from apscheduler.triggers.cron import CronTrigger

# 使用相对导入，因为所有 .py 文件都在 src 包中
from .optimizer import CloudflareOptimizer
from .heartbeat import check_best_ip
from .state import app_state
from .api import create_app  # 导入新的 api 模块


def setup_scheduler(optimizer: CloudflareOptimizer, config: configparser.ConfigParser) -> BackgroundScheduler:
    """配置并启动调度器"""
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    
    # 添加 fallback 增加健壮性
    optimize_cron = config.get('Scheduler', 'optimize_cron', fallback='0 */4 * * *')
    scheduler.add_job(
        optimizer.run_speed_test,
        trigger=CronTrigger.from_crontab(optimize_cron),
        id='job_optimize_ip',
        name='定时优选Cloudflare IP'
    )
    logging.info(f"已添加定时优选任务，Cron: {optimize_cron}")

    # 添加 fallback 增加健壮性
    heartbeat_cron = config.get('Scheduler', 'heartbeat_cron', fallback='*/5 * * * *')
    scheduler.add_job(
        lambda: check_best_ip(optimizer),
        trigger=CronTrigger.from_crontab(heartbeat_cron),
        id='job_heartbeat_check',
        name='最优IP心跳检测'
    )
    logging.info(f"已添加心跳检测任务，Cron: {heartbeat_cron}")
    
    scheduler.start()
    return scheduler

def main() -> None:
    # 1. 确定路径
    # 无论从哪里运行脚本，都能找到正确的项目根目录和配置目录
    # __file__ -> .../src/main.py
    # os.path.dirname(__file__) -> .../src
    # os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) -> .../ (项目根目录)
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
    CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, 'config.ini')

    # 确保配置目录存在
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # 2. 读取配置
    if not os.path.exists(CONFIG_FILE_PATH):
        logging.warning(f"配置文件未找到: {CONFIG_FILE_PATH}，将使用默认配置并创建文件。")
        config = configparser.ConfigParser()
        config['CloudflareSpeedTest'] = {
            'params': '-p 0 -o result.csv -url https://cf.xiu2.xyz/url -dn 10 -t 2 '
        }
        config['Scheduler'] = {
            'optimize_cron': '0 3 * * *',
            'heartbeat_cron': '*/5 * * * *'
        }
        config['API'] = {'port': 6788}
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    else:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH, encoding='utf-8')

    # 3. 初始化核心优选器，并传入配置目录
    optimizer = CloudflareOptimizer(config, config_dir=CONFIG_DIR)

    # 4. 下载/检查工具
    optimizer.download_and_extract_tool()

    # 5. 启动时先执行一次优选
    logging.info("程序启动，立即执行一次IP优选...")
    # 在新线程中执行，避免阻塞后续的API服务启动
    initial_run_thread = threading.Thread(target=optimizer.run_speed_test)
    initial_run_thread.start()

    # 6. 创建 Flask App
    app = create_app(optimizer)

    # 7. 配置并启动调度器
    scheduler = setup_scheduler(optimizer, config)

    # 8. 启动API服务
    api_port = config['API'].getint('port', 6788)
    logging.info(f"API服务将在 http://0.0.0.0:{api_port} 上启动")
    try:
        # 使用 waitress 作为生产级 WSGI 服务器
        serve(app, host='0.0.0.0', port=api_port)
    except (KeyboardInterrupt, SystemExit):
        logging.info("收到退出信号，正在关闭调度器...")
        scheduler.shutdown()
        logging.info("等待初次优选任务完成...")
        initial_run_thread.join() # 确保初次运行在退出前完成

if __name__ == '__main__':
    main()
