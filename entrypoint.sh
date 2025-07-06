#!/bin/sh
# 任何命令失败时立即退出，保证脚本的健壮性
set -e

# 从环境变量获取用户ID和组ID，如果未设置则使用默认值 1000
PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "Initializing container with UID: $PUID, GID: $PGID"

# 获取容器内预设用户 appuser 的当前 UID 和 GID
CURRENT_UID=$(id -u appuser)
CURRENT_GID=$(id -g appgroup)

# 当传入的 PGID 与容器内 GID 不一致时，修改组的 GID
if [ "$PGID" != "$CURRENT_GID" ]; then
    echo "Changing appgroup GID to $PGID"
    groupmod -o -g "$PGID" appgroup
fi

# 当传入的 PUID 与容器内 UID 不一致时，修改用户的 UID
if [ "$PUID" != "$CURRENT_UID" ]; then
    echo "Changing appuser UID to $PUID"
    usermod -o -u "$PUID" appuser
fi

# 授予对应用、数据、日志和配置目录的所有权
# 这样，当您挂载主机目录时，容器内的用户将具有正确的写入权限
echo "Taking ownership of /app, /data, /log, /config..."
chown -R appuser:appgroup /app /data /log /config

# 使用 gosu 切换到 appuser 用户，并执行 Dockerfile 的 CMD 中定义的命令 (即 "$@")
echo "Executing command as appuser: $@"
exec gosu appuser "$@"