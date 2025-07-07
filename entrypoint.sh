#!/bin/sh
set -e

# 默认用户ID和组ID。使用 1000 是一个常见的非 root 用户实践。
# 如果环境变量 PUID 或 PGID 未设置，则使用这些默认值。
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# 如果组ID不存在，则创建组
if ! getent group "$PGID" >/dev/null; then
    addgroup --gid "$PGID" appgroup
fi

# 如果用户ID不存在，则创建用户
if ! getent passwd "$PUID" >/dev/null; then
    adduser \
        --shell /bin/sh \
        --disabled-password \
        --uid "$PUID" \
        --gid "$PGID" \
        --gecos "Application User" \
        --no-create-home \
        appuser
fi

# 设置 /app/config 目录的所有权
# 这确保了无论主机上的用户是谁，容器内的应用都有权限写入挂载的卷
echo "Updating ownership of /app/config to $PUID:$PGID..."
chown -R "$PUID:$PGID" /app/config

# 使用 su-exec 切换到指定用户，并执行传递给脚本的命令 (CMD)
echo "Executing command as user $PUID:$PGID: $@"
exec su-exec "$PUID:$PGID" "$@"
