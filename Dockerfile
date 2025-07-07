# 使用官方的 Python 3.11 slim 版本作为基础镜像
FROM python:3.11-slim

# 设置环境变量，确保 Python 输出能立即被捕获，且不生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (ping)
# slim 镜像默认不包含 ping 和 su-exec 工具，需要手动安装
RUN apt-get update && apt-get install -y iputils-ping su-exec && \
    rm -rf /var/lib/apt/lists/*

# 安装依赖
# 先只复制 requirements.txt 文件，这样可以利用 Docker 的层缓存机制
# 只有当依赖变化时，才会重新执行 pip install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 entrypoint 脚本并赋予执行权限
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 复制应用程序代码
# 将 src 目录复制到容器的 /app/src
COPY src/ ./src/

# 将默认的 config 目录复制到容器中，作为备用
COPY config/ ./config/

# 暴露 API 服务的端口
EXPOSE 6788

# 设置 entrypoint
ENTRYPOINT ["entrypoint.sh"]

# 容器启动时执行的命令
CMD ["python", "-m", "src.main"]
