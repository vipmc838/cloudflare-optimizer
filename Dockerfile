# 使用官方的 Python 运行时作为父镜像
FROM python:3.11-slim

# 设置环境变量，避免 Python 输出缓冲
ENV PYTHONUNBUFFERED=1

# 安装 gosu 用于用户切换，并清理 apt 缓存
# gosu 是一个轻量级的 su/sudo 替代品，非常适合在容器中使用
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# 创建一个非 root 用户和组，后续将使用 PUID/PGID 动态修改
RUN groupadd -r appgroup --gid 1000 && \
    useradd --no-log-init -r -s /bin/false --uid 1000 -g appgroup appuser

# 根据您的 .gitignore 文件，创建应用、数据、日志和配置目录
RUN mkdir -p /app /data /logs /config

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装，利用 Docker 的层缓存机制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制入口点脚本并赋予执行权限
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 复制预置的数据文件（如 ip.txt, ipv6.txt）到镜像中
COPY data/ /app/data/

# 复制所有应用代码到工作目录
COPY . .

# 设置入口点，容器启动时会执行这个脚本
ENTRYPOINT ["entrypoint.sh"]

# 设置容器启动时执行的默认命令
# 假设您的 FastAPI 应用实例在 main.py 文件中，变量名为 app
# 如果您的文件名或变量名不同，请修改 "main:app"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6788"]
