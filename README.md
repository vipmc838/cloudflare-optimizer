# Cloudflare IP 优选服务 docker打包版

🌩 自动测试 Cloudflare CDN 延迟和速度，自动优选最佳IP地址，并提供API接口。

## 特别感谢

XIU2大佬的[cloudflare优选IP](https://github.com/XIU2/CloudflareSpeedTest?tab=readme-ov-file)项目

thsrite大佬的[Cloudflare IP优选](https://github.com/jxxghp/MoviePilot-Plugins/blob/main/plugins/cloudflarespeedtest)插件项目


## 功能特性

- **自动优选**: 根据预设的 Cron 表达式，定时自动执行 IP 速度测试。
- **心跳检测**: 定期检查当前最优 IP 的可用性，确保其稳定可靠。
- **RESTful API**: 提供简单的 API 接口，方便其他应用获取最优 IP 和测试结果。
- **手动触发**: 支持通过 API 手动触发一次优选任务。
- **Docker 化部署**: 提供 Dockerfile 和 Docker Compose 文件，实现一键部署和运行。
- **CI/CD**: 集成 GitHub Actions，在代码推送到 `main` 分支后自动构建并发布 Docker 镜像到 Docker Hub。


## 快速开始


### 使用Docker-Compose运行
```docker-compose
version: '3.8'

services:
  cf-optimizer:
    image: l429609201/cloudflare-optimizer:latest
    container_name: cf-optimizer
    #network_mode: host
    restart: always
    ports:
      # 将主机的 6788 端口映射到容器的 6788 端口
      # 如果端口冲突，可以修改左边的端口，例如 "8080:6788"
      - "6788:6788"
    volumes:
      # 将本地的 config 目录挂载到容器内，用于持久化配置和结果
      - ./config:/app/config
    environment:
      # 设置容器时区，与 config.ini 中的时区保持一致，以确保定时任务准确执行
      - TZ=Asia/Shanghai
      - PUID=1000
      - PGID=1000

```

## 📖 OpenWRT 自动更新host

 - 在配置文件中配置
   
### 支持通过ssh的方式，更新openwrt的host文件或者更新mosdns的自定义host规则
 - ##自动CF优选开始##
 - xxx.xxx 104.25.136.141
 - xxx.xxx 104.25.136.141
 - xxx.xxx 104.25.136.141
 - xxx.xxx 104.25.136.141
 - xxx.xxx 104.25.136.141
 - ##自动CF优选结束##

---

## 📖 API 文档

### 获取最优 IP
- **URL**: `/api/best_ip`
- **Method**: `GET`
- **Success Response**: `{"best_ip": "172.67.7.111"}`
- **Error Response**: `{"error": "最优IP尚未确定"}`, `status: 404`

### 获取最近一次的完整测试结果
- **URL**: `/api/results`
- **Method**: `GET`
- **Success Response**: `[{"ip": "...", "latency": "...", ...}]`
- **Error Response**: `{"error": "尚未有优选结果"}`, `status: 404`

### 手动触发一次优选任务
- **URL**: `/api/run_test`
- **Method**: `POST`
- **Success Response**: `{"message": "IP优选任务已启动"}`, `status: 202`
- **Error Response**: `{"message": "优选任务已在运行中，请稍后再试"}`, `status: 429`

---
