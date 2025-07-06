from fastapi import FastAPI, HTTPException, Security, Depends, Query
from fastapi.security import APIKeyHeader
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .cf_optimizer import CloudflareOptimizer
from .config_loader import config
import logging
import time
from pathlib import Path
import json

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")
cf_optimizer = CloudflareOptimizer()
logger = logging.getLogger("api")

# 挂载静态文件目录
#app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "static"), name="static")
#app.mount("/static", StaticFiles(directory="/app/static"), name="static")

def get_api_key(api_key: str = Security(api_key_header)):
    config_key = config.get('cloudflare', 'api_key')
    if api_key != config_key:
        # 安全记录API密钥尝试
        masked_key = api_key[:4] + "****" if len(api_key) > 4 else "****"
        logger.warning(f"Invalid API key attempt: {masked_key}")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

def format_parameters(params: dict) -> str:
    """格式化参数为易读的HTML"""
    html = "<table class='table'><thead><tr><th>参数</th><th>值</th><th>说明</th></tr></thead><tbody>"
    
    # 参数说明映射
    param_descriptions = {
        "n": "延迟测速线程数；越多测速越快，但性能消耗更大（默认200，最大1000）",
        "t": "延迟测速次数；单个IP测速次数（默认4次）",
        "dn": "下载测速数量；从最低延迟起进行下载测速的数量（默认10个）",
        "dt": "下载测速时间；单个IP下载测速最长时间（秒）（默认10秒）",
        "tp": "测速端口；延迟/下载测速使用的端口（默认443）",
        "url": "测速地址；HTTPing模式使用的URL（默认https://cf.xiu2.xyz/url）",
        "httping": "是否使用HTTPing模式（默认TCPing）",
        "httping_code": "HTTPing有效状态码（默认200）",
        "cfcolo": "匹配指定地区（机场地区码，逗号分隔）",
        "tl": "平均延迟上限（ms）",
        "tll": "平均延迟下限（ms）",
        "tlr": "丢包率上限（0.0-1.0）",
        "sl": "下载速度下限（MB/s）",
        "p": "显示结果数量（0表示不显示）",
        "f": "IP段数据文件路径",
        "ip": "直接指定的IP段数据",
        "o": "结果输出文件路径",
        "dd": "是否禁用下载测速",
        "allip": "是否测速全部IP",
        "debug": "是否启用调试模式",
        "cron": "定时任务cron表达式",
        "ipv4": "是否启用IPv4测速",
        "ipv6": "是否启用IPv6测速",
        "re_install": "是否重新安装工具",
        "proxy": "代理服务器地址",
        "api_port": "API服务端口",
        "api_key": "API认证密钥"
    }
    
    for key, value in params.items():
        description = param_descriptions.get(key, "无说明")
        html += f"<tr><td><strong>{key}</strong></td><td>{value}</td><td>{description}</td></tr>"
    
    html += "</tbody></table>"
    return html

def format_api_docs() -> str:
    """生成API文档HTML"""
    base_url = "http://localhost:6788"  # 实际部署时应替换为真实域名
    
    html = """
    <h2>API 文档</h2>
    <table class="table">
        <thead>
            <tr>
                <th>端点</th>
                <th>方法</th>
                <th>说明</th>
                <th>调用示例</th>
            </tr>
        </thead>
        <tbody>
    """
    
    apis = [
        {
            "endpoint": "/run",
            "method": "GET",
            "description": "手动触发Cloudflare IP优选",
            "example": f"curl -H 'X-API-Key: your-key' {base_url}/run"
        },
        {
            "endpoint": "/results",
            "method": "GET",
            "description": "获取优选结果列表（可选top参数限制数量）",
            "example": f"curl -H 'X-API-Key: your-key' {base_url}/results?top=5"
        },
        {
            "endpoint": "/best",
            "method": "GET",
            "description": "获取最优IP及其完整数据",
            "example": f"curl -H 'X-API-Key: your-key' {base_url}/best"
        },
        {
            "endpoint": "/ip",
            "method": "GET",
            "description": "仅获取最优IP地址（纯文本响应）",
            "example": f"curl -H 'X-API-Key: your-key' {base_url}/ip"
        },
        {
            "endpoint": "/parameters",
            "method": "GET",
            "description": "获取当前使用的所有参数",
            "example": f"curl -H 'X-API-Key: your-key' {base_url}/parameters"
        }
    ]
    
    for api in apis:
        html += f"""
        <tr>
            <td>{api['endpoint']}</td>
            <td>{api['method']}</td>
            <td>{api['description']}</td>
            <td><code>{api['example']}</code></td>
        </tr>
        """
    
    html += "</tbody></table>"
    return html

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """项目仪表板"""
    # 获取当前配置参数
    params = config.get_args_dict()
    cron = config.get('cloudflare', 'cron')
    api_port = config.get('cloudflare', 'api_port', fallback=6788)
    
    # 移除API密钥显示
    if 'api_key' in params:
        params['api_key'] = "****** (出于安全考虑不显示)"
    
    # 尝试获取最优IP信息
    best_ip_info = None
    try:
        results = cf_optimizer.get_results()
        if results:
            best_ip_info = results[0]
    except:
        pass
    
    # 生成HTML内容
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cloudflare IP 优选服务</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; background-color: #f8f9fa; }}
            .card {{ margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .table {{ font-size: 0.9rem; }}
            .table th {{ background-color: #e9ecef; }}
            .ip-info {{ font-size: 1.2rem; }}
            .param-name {{ font-weight: bold; }}
            .api-example {{ font-family: monospace; background-color: #f8f9fa; padding: 5px; border-radius: 3px; }}
            .security-note {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row">
                <div class="col">
                    <h1 class="text-center mb-4">🌩 Cloudflare IP 优选服务</h1>
                    
                    <div class="card">
                        <div class="card-header bg-primary text-white">
                            <h5 class="mb-0">服务状态</h5>
                        </div>
                        <div class="card-body">
                            <p><strong>运行时间：</strong> {time.ctime()}</p>
                            <p><strong>定时任务：</strong> {cron}</p>
                            <p><strong>API端口：</strong> {api_port}</p>
                            <p class="security-note">🔒 API密钥已隐藏，请妥善保管</p>
                        </div>
                    </div>
    """
    
    # 最优IP信息
    if best_ip_info:
        html += f"""
        <div class="card">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">当前最优 IP</h5>
            </div>
            <div class="card-body">
                <div class="ip-info">
                    <p><strong>IP地址：</strong> {best_ip_info.get('IP地址', 'N/A')}</p>
                    <p><strong>延迟：</strong> {best_ip_info.get('延迟', 'N/A')} ms</p>
                    <p><strong>抖动：</strong> {best_ip_info.get('抖动', 'N/A')} ms</p>
                    <p><strong>丢包率：</strong> {best_ip_info.get('丢包率', 'N/A')}%</p>
                    <p><strong>下载速度：</strong> {best_ip_info.get('下载速度', 'N/A')} MB/s</p>
                    <p><strong>位置：</strong> {best_ip_info.get('城市', 'N/A')}, {best_ip_info.get('国家', 'N/A')}</p>
                    <p><strong>地区码：</strong> {best_ip_info.get('地区码', 'N/A')}</p>
                </div>
            </div>
        </div>
        """
    else:
        html += """
        <div class="card">
            <div class="card-header bg-warning">
                <h5 class="mb-0">当前最优 IP</h5>
            </div>
            <div class="card-body">
                <p class="text-center">尚未运行优选或没有可用结果</p>
            </div>
        </div>
        """
    
    # 参数表格
    html += f"""
        <div class="card">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">当前优选参数</h5>
            </div>
            <div class="card-body">
                {format_parameters(params)}
            </div>
        </div>
    """
    
    # API文档
    html += f"""
        <div class="card">
            <div class="card-header bg-secondary text-white">
                <h5 class="mb-0">API 文档</h5>
            </div>
            <div class="card-body">
                {format_api_docs()}
                <div class="alert alert-warning mt-3">
                    <strong>安全提示：</strong>
                    <ul>
                        <li>所有API请求都需要在Header中添加 <code>X-API-Key: your-secret-key</code></li>
                        <li>请勿将API密钥泄露给他人</li>
                        <li>建议定期更换API密钥</li>
                        <li>仅允许受信任的IP访问API服务</li>
                    </ul>
                </div>
            </div>
        </div>
    """
    
    html += """
            </div>
        </div>
        <footer class="mt-5 text-center text-muted">
            <p>Cloudflare IP 优选服务 &copy; 2023</p>
        </footer>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)

@app.get("/run", dependencies=[Depends(get_api_key)])
def run_optimization():
    """手动触发优选"""
    logger.info("Manual optimization triggered via API")
    result_file = cf_optimizer.run_optimization()
    if result_file:
        return {
            "status": "success",
            "message": "Optimization completed",
            "result_file": str(result_file)
        }
    return {
        "status": "error",
        "message": "Optimization failed"
    }

@app.get("/results", dependencies=[Depends(get_api_key)])
def get_optimization_results(top: int = Query(0, description="返回前N个结果，0表示全部")):
    """获取优选结果"""
    logger.info(f"API获取优选结果，数量: {'全部' if top == 0 else top}")
    results = cf_optimizer.get_results()
    if not results:
        return {
            "status": "error",
            "message": "No results available"
        }
    
    # 返回指定数量的结果
    if top > 0:
        results = results[:top]
    
    return {
        "status": "success",
        "count": len(results),
        "results": results
    }

@app.get("/best", dependencies=[Depends(get_api_key)])
def get_best_ip():
    """获取最优IP及其完整数据"""
    logger.info("API获取最优IP详情")
    results = cf_optimizer.get_results()
    if not results:
        return {
            "status": "error",
            "message": "No results available"
        }
    
    # 第一个结果是最优IP
    best_ip = results[0]
    return {
        "status": "success",
        "best_ip": best_ip,
        "detail": {
            "ip": best_ip.get("IP地址", ""),
            "latency": best_ip.get("延迟", ""),
            "jitter": best_ip.get("抖动", ""),
            "loss": best_ip.get("丢包率", ""),
            "speed": best_ip.get("下载速度", "")
        }
    }

@app.get("/ip", dependencies=[Depends(get_api_key)], response_class=PlainTextResponse)
def get_ip_address():
    """只返回最优IP地址（纯文本）"""
    logger.info("API获取最优IP文本")
    results = cf_optimizer.get_results()
    if not results:
        raise HTTPException(status_code=404, detail="No results available")
    
    # 返回第一个结果的IP地址
    return results[0].get("IP地址", "")

@app.get("/parameters", dependencies=[Depends(get_api_key)])
def get_parameters():
    """获取当前使用的参数"""
    logger.info("API获取配置参数")
    return {
        "status": "success",
        "parameters": config.get_args_dict()
    }
