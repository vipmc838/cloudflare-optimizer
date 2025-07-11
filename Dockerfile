# 使用官方的 Python 3.11 slim 版本作为基础镜像
FROM python:3.11-slim

# 设置环境变量，确保 Python 输出能立即被捕获，且不生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 接收构建时参数，并设置默认值
ARG PUID=1000
ARG PGID=1000

# 安装系统依赖并创建用户
# 这种方法将用户权限在构建时固化到镜像中
RUN apt-get update && apt-get install -y iputils-ping && \
    # 检查并删除可能冲突的现有组和用户
    if getent group ${PGID} > /dev/null; then delgroup $(getent group ${PGID} | cut -d: -f1); fi && \
    if getent passwd ${PUID} > /dev/null; then deluser $(getent passwd ${PUID} | cut -d: -f1); fi && \
    # 创建指定ID的用户和组
    addgroup --gid ${PGID} appgroup && \
    adduser --shell /bin/sh --disabled-password --uid ${PUID} --gid ${PGID} appuser && \
    # 清理apt缓存
    rm -rf /var/lib/apt/lists/*

# 安装依赖
# 先只复制 requirements.txt 文件，这样可以利用 Docker 的层缓存机制
# 只有当依赖变化时，才会重新执行 pip install
COPY requirements.txt .
# 以 root 身份安装，确保有权限写入 /usr/local/lib
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码
# 将 src 目录复制到容器的 /app/src
COPY src/ ./src/

# 将默认的 config 目录复制到容器中，作为备用
COPY config/ ./config/

# 复制 Web UI 相关文件
COPY templates/ ./templates/
COPY static/ ./static/

# 更改工作目录所有权为新创建的用户
RUN chown -R appuser:appgroup /app

# 暴露 API 服务的端口
EXPOSE 6788

# 切换到非 root 用户
USER appuser

# 容器启动时执行的命令
CMD ["python", "-m", "src.main"]
