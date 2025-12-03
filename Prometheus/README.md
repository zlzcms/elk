# Prometheus Docker Compose 部署指南

## 概述
这个项目使用Docker Compose部署Prometheus监控系统，包含以下组件：
- **Prometheus**: 监控和告警系统
- **Grafana**: 数据可视化和仪表板
- **Node Exporter**: 系统指标收集器

## 快速开始

### 1. 启动服务
```bash
cd /home/user/tool/Prometheus
docker-compose up -d
```

### 2. 访问服务
- **Prometheus Web UI**: http://localhost:9090
- **Grafana Dashboard**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin`
- **Node Exporter**: http://localhost:9100

### 3. 停止服务
```bash
docker-compose down
```

## 服务说明

### Prometheus (端口: 9090)
- 主要的监控和告警系统
- 配置文件: `prometheus.yml`
- 数据存储: Docker volume `prometheus_data`

### Grafana (端口: 3000)
- 数据可视化和仪表板
- 默认管理员账户: admin/admin
- 数据存储: Docker volume `grafana_data`

### Node Exporter (端口: 9100)
- 收集系统指标（CPU、内存、磁盘等）
- 自动配置为监控主机系统

## 配置说明

### prometheus.yml
- `scrape_interval`: 抓取间隔（15秒）
- `evaluation_interval`: 规则评估间隔（15秒）
- `scrape_configs`: 监控目标配置

### 添加新的监控目标
在 `prometheus.yml` 的 `scrape_configs` 部分添加新的job：

```yaml
- job_name: 'your-service'
  static_configs:
    - targets: ['your-service:port']
```

## 数据持久化
- Prometheus数据存储在 `prometheus_data` volume中
- Grafana数据存储在 `grafana_data` volume中
- 即使容器重启，数据也会保留

## 常用命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs prometheus
docker-compose logs grafana
docker-compose logs node-exporter
```

### 重启服务
```bash
docker-compose restart prometheus
```

### 更新配置后重新加载
```bash
# 修改prometheus.yml后，重新加载配置
curl -X POST http://localhost:9090/-/reload
```

## 故障排除

### 端口冲突
如果端口被占用，可以修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "9091:9090"  # 将9090改为9091
```

### 权限问题
确保Docker有权限访问系统目录：
```bash
sudo chmod 755 /proc /sys
```

### 查看详细日志
```bash
docker-compose logs -f prometheus
```

## 下一步
1. 在Grafana中添加Prometheus数据源
2. 导入预制的仪表板
3. 配置告警规则
4. 添加更多监控目标
