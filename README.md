# Cloudflare IP 优选服务 docker打包版

🌩 自动测试 Cloudflare CDN 延迟和速度，自动优选最佳IP地址，并提供API接口。

## 特别感谢

XIU2大佬的[cloudflare优选IP](https://github.com/XIU2/CloudflareSpeedTest?tab=readme-ov-file)项目

thsrite大佬的[Cloudflare IP优选](https://github.com/jxxghp/MoviePilot-Plugins/blob/main/plugins/cloudflarespeedtest)插件项目


## 功能特性

- 定时自动优选Cloudflare IP
- 完整的API接口服务
- 详细的性能监控日志
- Docker容器化支持
- 可视化仪表板

## 快速开始

### 使用Docker运行

```docker-cli
docker run -d \
  --name cf-optimizer \
  -p 6788:6788 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/config:/app/config \
  l429609201/cloudflare-ip-optimizer:latest
```

### 使用Docker-Compose运行
```docker-compose
version: '3.8'

services:
  cf-optimizer:
    image: l429609201/cloudflare-ip-optimizer:latest
    container_name: cf-ip-optimizer
    restart: unless-stopped
    ports:
      - "6788:6788"
    volumes:
      - ./data:/app/data
      - ./log:/app/log
      - ./config:/app/config
```
