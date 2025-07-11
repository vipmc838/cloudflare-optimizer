from flask import Flask, jsonify, current_app, render_template, request
from .optimizer import CloudflareOptimizer  # 确保使用相对导入
from .state import app_state
import threading
import logging
import configparser

def create_app(optimizer: CloudflareOptimizer, template_folder: str, static_folder: str) -> Flask:
    """创建并配置 Flask 应用实例 (Application Factory)"""
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config['OPTIMIZER_INSTANCE'] = optimizer

    @app.route('/', methods=['GET'])
    def index():
        return render_template('index.html')

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

    @app.route('/api/config', methods=['GET'])
    def get_config():
        config: configparser.ConfigParser = current_app.config['CONFIG']
        # 将配置转换为字典，以便 JSON 序列化
        config_dict = {section: dict(config.items(section)) for section in config.sections()}
        return jsonify(config_dict)

    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        # 读取日志文件内容并返回
        log_file_path = current_app.config['LOG_FILE_PATH']
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            return jsonify(logs)
        except FileNotFoundError:
            logging.warning(f"日志文件未找到: {log_file_path}")
            return jsonify({"error": "日志文件未找到"}), 404

    @app.route('/api/config', methods=['POST'])  # 修改为 POST 方法
    def update_config():
        config_file_path = current_app.config['CONFIG_FILE_PATH']
        try:
            # 直接获取文本内容
            new_config = request.get_data(as_text=True)

            # 写入文件
            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(new_config)

            # 重新加载配置到 Flask app
            current_app.config['CONFIG'].read(config_file_path, encoding='utf-8')
            return jsonify({"message": "配置已更新"}), 200  # 返回成功消息
        except Exception as e:
            logging.error(f"Failed to update config: {e}")
            return jsonify({"error": f"Failed to update config: {e}"}), 500
    return app
