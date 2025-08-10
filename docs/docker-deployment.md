# Docker Deployment Guide

Complete guide for deploying the Japanese Accommodation Availability Checker using Docker.

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd gassho-zukuri-checker

# Configure
cp config.example.json config.json
# Edit config.json with your settings

# Deploy
docker compose up -d
```

## Docker Compose Files

### Standard Deployment: `docker-compose.yml`

```yaml
services:
  accommodation-checker:
    build: .
    container_name: gassho-zukuri-checker
    restart: unless-stopped
    volumes:
      - ./config.json:/app/config.json:ro
    environment:
      - CONFIG_PATH=/app/config.json
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - checker-network
    healthcheck:
      test: ["CMD", "python", "-c", "import asyncio; ..."]
      interval: 60s
      timeout: 10s
      retries: 3

networks:
  checker-network:
    driver: bridge
```

### Testing with Mock: `docker-compose.test.yml`

```yaml
services:
  accommodation-checker:
    environment:
      - SINGLE_RUN=true
    restart: "no"
  
  mock-notification:
    build:
      context: ./docker
      dockerfile: Dockerfile.mock
    ports:
      - "8080:3000"
```

## Building the Image

### Multi-Stage Build Process

The Dockerfile uses a multi-stage build:

1. **Builder Stage**: Installs dependencies and Playwright browsers
2. **Runtime Stage**: Minimal production image with only required components

```bash
# Build manually
docker build -t accommodation-checker .

# Build with compose
docker compose build
```

### Build Arguments

```bash
# Custom Python version
docker build --build-arg PYTHON_VERSION=3.11 .
```

## Configuration

### Environment Variables

Set in `docker-compose.yml` or `.env` file:

```bash
# .env file
CONFIG_PATH=/app/config.json
LOG_LEVEL=INFO
NOTIFICATION_ENDPOINT=https://your-webhook.com/notify
```

### Volume Mounts

```yaml
volumes:
  # Configuration (read-only)
  - ./config.json:/app/config.json:ro
  
  # Logs (optional)
  - ./logs:/app/logs
  
  # Browser cache (optional, for performance)
  - browser-cache:/home/appuser/.cache/ms-playwright
```

## Health Checks

### Container Health Check

Built-in health check verifies service status:

```bash
# Check health status
docker compose ps

# View health check logs
docker inspect gassho-zukuri-checker --format='{{.State.Health.Status}}'
```

### Custom Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 10s
  start_period: 30s
  retries: 3
```

## Networking

### Internal Network

Services communicate via dedicated Docker network:

```yaml
networks:
  checker-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### External Access

```yaml
services:
  accommodation-checker:
    ports:
      - "8080:8080"  # Health check endpoint
```

## Persistent Data

### Volumes for Data Persistence

```yaml
volumes:
  # Configuration
  config-volume:
    driver: local
    driver_opts:
      type: bind
      device: ./config
      o: bind
  
  # Logs
  logs-volume:
    driver: local

services:
  accommodation-checker:
    volumes:
      - config-volume:/app/config:ro
      - logs-volume:/app/logs
```

## Production Deployment

### Resource Limits

```yaml
services:
  accommodation-checker:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Security Configuration

```yaml
services:
  accommodation-checker:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
```

### Logging Configuration

```yaml
services:
  accommodation-checker:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Monitoring Integration

### Prometheus Metrics

```yaml
services:
  accommodation-checker:
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=8080"
      - "prometheus.io/path=/metrics"
```

### Log Aggregation

```yaml
services:
  accommodation-checker:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: localhost:24224
        tag: accommodation-checker
```

## Scaling

### Multiple Instances

```yaml
services:
  accommodation-checker:
    deploy:
      replicas: 3
    environment:
      - INSTANCE_ID={{.Task.Slot}}
```

### Load Balancing

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - accommodation-checker
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

## Troubleshooting

### View Logs

```bash
# All logs
docker compose logs

# Specific service
docker compose logs accommodation-checker

# Follow logs
docker compose logs -f accommodation-checker

# Last 100 lines
docker compose logs --tail=100 accommodation-checker
```

### Debug Container

```bash
# Access running container
docker compose exec accommodation-checker bash

# Run debug commands
docker compose exec accommodation-checker python -c "import sys; print(sys.path)"
```

### Health Check Debugging

```bash
# Manual health check
docker compose exec accommodation-checker \
  python -c "import asyncio; from main import AccommodationChecker; from config import load_config; print(asyncio.run(AccommodationChecker(load_config()).health_check()))"
```

## Common Issues

### Browser Installation

```bash
# Rebuild with fresh browser install
docker compose build --no-cache
```

### Permission Issues

```bash
# Fix file permissions
sudo chown -R 1000:1000 ./config.json
```

### Memory Issues

```bash
# Increase memory limit
docker compose up --memory=1g
```

## Maintenance

### Updates

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Cleanup

```bash
# Remove old containers
docker compose down --rmi all

# Clean up volumes
docker volume prune

# Full cleanup
docker system prune -a
```

## Best Practices

1. **Use specific image tags** instead of `latest`
2. **Mount configuration as read-only**
3. **Set resource limits** for production
4. **Use health checks** for monitoring
5. **Configure log rotation** to prevent disk fill
6. **Regular backup** of configuration and logs
7. **Monitor resource usage** and scale accordingly