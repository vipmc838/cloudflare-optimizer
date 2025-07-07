# d:\桌面\cloudflare-ip-optimizer-main\src\heartbeat.py
import subprocess
import sys
import logging
from .state import app_state

def check_best_ip(optimizer_instance):
    """
    Ping 当前的最优IP，如果失败则触发一次新的优选。
    """
    if not app_state.best_ip:
        logging.info("心跳检测：未设置最优IP，跳过本次检测。")
        return

    logging.info(f"心跳检测：正在 Ping 最优IP -> {app_state.best_ip}")

    # 根据不同操作系统构造 ping 命令
    # -c 1 (Linux/macOS) / -n 1 (Windows): 发送1个包
    # -W 2 (Linux) / -w 2000 (Windows): 超时2秒
    if sys.platform == "win32":
        command = ["ping", "-n", "1", "-w", "2000", app_state.best_ip]
    else:
        command = ["ping", "-c", "1", "-W", "2", app_state.best_ip]

    try:
        # 使用 subprocess.run 来执行命令，并隐藏输出
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logging.info(f"心跳检测成功：IP {app_state.best_ip} 响应正常。")
        else:
            logging.warning(f"心跳检测失败：IP {app_state.best_ip} 无法访问。将触发一次新的IP优选。")
            # 调用优选实例来运行测试
            optimizer_instance.run_speed_test()

    except Exception as e:
        logging.error(f"执行 Ping 命令时出错: {e}")
