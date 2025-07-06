import time
import logging
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
        cron = config.get('cloudflare', 'cron')
        self.logger.info(f"Starting scheduler with cron: {cron}")
        
        # 添加定时任务
        self.scheduler.add_job(
            self.run_optimization_task,
            trigger=CronTrigger.from_crontab(cron),
            id="cloudflare_optimization"
        )
        
        # 立即运行一次
        self.run_optimization_task()
        
        self.scheduler.start()
        self.logger.info("Scheduler started")
        
        try:
            while True:
                time.sleep(3600)  # 主线程休眠
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")

    def run_optimization_task(self):
        self.logger.info("Starting Cloudflare optimization task")
        result_file = self.cf_optimizer.run_optimization()
        if result_file:
            self.logger.info(f"Optimization completed! Results saved to: {result_file}")
        else:
            self.logger.warning("Optimization failed")