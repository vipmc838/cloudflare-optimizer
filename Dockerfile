# 使用官方的 Python 运行时作为父镜像
FROM python:3.11-slim

# 设置环境变量，避免 Python 输出缓冲
ENV PYTHONUNBUFFERED=1

# 安装 gosu 用于用户切换，并清理 apt 缓存
# gosu 是一个轻量级的 su/sudo 替代品，非常适合在容器中使用
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# ✨ 1. 接收从 Unraid (或 docker-compose) 传来的环境变量，并设置默认值 ✨
ARG PUID=1000
ARG PGID=1000

# ✨✨✨ START: 决定性的修复 ✨✨✨
# 1. 检查目标 PUID 是否已被占用，如果被占用，就删除那个用户
#    我们用 `getent passwd ${PUID}` 来查找，如果找到了，第一列就是用户名
RUN if getent passwd ${PUID} > /dev/null; then \
    echo "User with PUID ${PUID} already exists, deleting it."; \
    EXISTING_USER=$(getent passwd ${PUID} | cut -d: -f1); \
    deluser $EXISTING_USER; \
    fi && \
    # 2. 现在可以安全地创建我们自己的用户和组了
    groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -s /bin/sh -m appuser
# ✨✨✨ END: 决定性的修复 ✨✨✨

# 根据您的 .gitignore 文件，创建应用、数据、日志和配置目录
RUN mkdir -p /app /data /logs /config && chown -R appuser:appgroup /app /data /logs /config

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装，利用 Docker 的层缓存机制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有应用代码到工作目录
COPY . .

# ✨ 4. 切换到这个新创建的非 root 用户 ✨
USER appuser

# 设置容器启动时执行的默认命令
# 假设您的 FastAPI 应用实例在 main.py 文件中，变量名为 app
# 如果您的文件名或变量名不同，请修改 "main:app"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6788"]
