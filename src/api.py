from flask import Flask, jsonify
from .optimizer import CloudflareOptimizer  # 确保使用相对导入
from .state import app_state
import threading

def create_app(optimizer: CloudflareOptimizer) -> Flask:
    """创建并配置 Flask 应用实例 (Application Factory)"""
    app = Flask(__name__)
    app.config['OPTIMIZER_INSTANCE'] = optimizer

    @app.route('/api/best_ip', methods=['GET'])
    def get_best_ip():
        if app_state.best_ip:
            return jsonify({"best_ip": app_state.best_ip})
        return jsonify({"error": "最优IP尚未确定"}), 404

    @app.route('/api/results', methods=['GET'])
    def get_results():
        if app_state.last_results:
            return jsonify(app_state.last_results)
        return jsonify({"error": "尚未有优选结果"}), 404

    @app.route('/api/run_test', methods=['POST'])
    def run_test_manual():
        # 从 app.config 获取 optimizer 实例
        optimizer_instance: CloudflareOptimizer = app.config['OPTIMIZER_INSTANCE']
        # 在后台线程中运行，避免阻塞API请求
        if not app_state.optimizer_lock.locked():
            thread = threading.Thread(target=optimizer_instance.run_speed_test)
            thread.start()
            return jsonify({"message": "IP优选任务已启动"}), 202
        else:
            return jsonify({"message": "优选任务已在运行中，请稍后再试"}), 429
            
    return app
