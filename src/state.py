# d:\桌面\cloudflare-ip-optimizer-main\src\state.py
import threading

class AppState:
    """
    用于在不同模块间共享应用程序状态的单例类。
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppState, cls).__new__(cls)
            # 初始化状态变量
            cls._instance.best_ip = None
            cls._instance.last_results = []
            # 使用锁来确保优选任务不会并发执行
            cls._instance.optimizer_lock = threading.Lock()
        return cls._instance

# 创建一个全局唯一的实例
app_state = AppState()
