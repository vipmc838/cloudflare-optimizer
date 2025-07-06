# cloudflare-ip-optimizer
# Cloudflare IP 优选服务

🌩 自动测试 Cloudflare CDN 延迟和速度，自动优选最佳IP地址，并提供API接口。

## 功能特性

- 定时自动优选Cloudflare IP
- 完整的API接口服务
- 详细的性能监控日志
- Docker容器化支持
- 可视化仪表板

## 快速开始

### 使用Docker运行

```bash
docker run -d \
  --name cf-optimizer \
  -p 6788:6788 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/config:/app/config \
  yourusername/cloudflare-ip-optimizer:latest
