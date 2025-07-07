import time
import logging
import platform
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from .config_loader import config
from .cf_optimizer import CloudflareOptimizer

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.cf_optimizer = CloudflareOptimizer()
        self.logger = logging.getLogger("scheduler")
    
    def start(self):
        # --- 常规优选任务 ---
        cron = config.get('cloudflare', 'cron')
        self.logger.info(f"Starting scheduler with cron: {cron}")
        self.scheduler.add_job(
            self.run_optimization_task,
            trigger=CronTrigger.from_crontab(cron),
            id="cloudflare_optimization"
        )
        
        # --- 心跳检测任务 ---
        heartbeat_enabled = config.getboolean('cloudflare', 'heartbeat_enabled', fallback=True)
        if heartbeat_enabled:
            heartbeat_cron = config.get('cloudflare', 'heartbeat_cron', fallback='*/5 * * * *')
            self.logger.info(f"Enabling heartbeat service with cron: {heartbeat_cron}")
            self.scheduler.add_job(
                self.run_heartbeat_task,
                trigger=CronTrigger.from_crontab(heartbeat_cron),
                id="heartbeat_check"
            )
        else:
            self.logger.info("Heartbeat service is disabled.")
            
        # 立即运行一次
        self.run_optimization_task()
        
        self.scheduler.start()
        self.logger.info("Scheduler started")

    def run_heartbeat_task(self):
        """执行心跳检测任务，Ping当前最优IP"""
        self.logger.info("Running heartbeat check...")
        
        # 1. 获取当前最优IP
        results = self.cf_optimizer.get_results()
        if not results:
            self.logger.warning("Heartbeat: No optimization results found. Skipping ping check.")
            return
            
        best_ip = results[0].get('ip')
        if not best_ip:
            self.logger.warning("Heartbeat: Could not find a valid IP in the results. Skipping ping check.")
            return
            
        self.logger.info(f"Heartbeat: Pinging best IP: {best_ip}")
        
        # 2. 执行Ping操作
        ping_count = config.get('cloudflare', 'heartbeat_ping_count', fallback='2')
        ping_timeout = config.get('cloudflare', 'heartbeat_ping_timeout', fallback='3')
        
        system = platform.system().lower()
        if system == "windows":
            # Windows: -n 是次数, -w 是毫秒
            command = ["ping", "-n", ping_count, "-w", str(int(ping_timeout) * 1000), best_ip]
        else:
            # Linux/macOS: -c 是次数, -W 是秒
            command = ["ping", "-c", ping_count, "-W", ping_timeout, best_ip]
        
        # 使用 subprocess.run 来执行命令并捕获返回码
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.logger.info(f"Heartbeat: IP {best_ip} is reachable. No action needed.")
        else:
            self.logger.warning(f"Heartbeat: IP {best_ip} is NOT reachable (ping failed). Triggering immediate optimization.")
            self.run_optimization_task()

    def run_optimization_task(self):
        self.logger.info("Starting Cloudflare optimization task")
        result_file = self.cf_optimizer.run_optimization()
        if result_file:
            self.logger.info(f"Optimization completed! Results saved to: {result_file}")
        else:
            self.logger.warning("Optimization failed")
