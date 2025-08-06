# Production Deployment Guide

Complete guide for deploying the Japanese Accommodation Availability Checker in production environments.

## Pre-Deployment Checklist

### Infrastructure Requirements

- **Server Resources**: Minimum 1 CPU core, 512MB RAM
- **Network Access**: Outbound HTTPS for scraping and notifications
- **Container Runtime**: Docker Engine 20.10+ and Docker Compose 2.0+
- **Storage**: 2GB for container images and logs
- **Monitoring**: Log aggregation and metrics collection setup

### Security Requirements

- [ ] TLS certificates configured
- [ ] Firewall rules configured
- [ ] Network segmentation implemented
- [ ] Resource limits defined
- [ ] Non-root container execution
- [ ] Secrets management configured

### Configuration Requirements

- [ ] Production configuration file created
- [ ] Notification endpoints tested
- [ ] Target dates defined
- [ ] Logging levels configured
- [ ] Health check endpoints accessible

## Production Configuration

### Environment-Specific Config

Create production configuration file:

```json
{
  "target_dates": ["2025-03-15", "2025-03-16", "2025-03-17"],
  "notification_endpoint": "https://api.yourservice.com/accommodations/webhook",
  "log_level": "INFO",
  "check_interval_seconds": 300,
  "retry_attempts": 5,
  "timeout_seconds": 45
}
```

### Environment Variables

```bash
# /etc/environment or systemd service file
CONFIG_PATH=/opt/ryokan-checker/config.json
LOG_LEVEL=INFO
NOTIFICATION_ENDPOINT=https://api.yourservice.com/webhook
```

### Production Docker Compose

```yaml
version: '3.8'

services:
  accommodation-checker:
    build: .
    image: accommodation-checker:1.0.0
    container_name: ryokan-checker-prod
    restart: unless-stopped
    
    # Security
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    
    # Resources
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
    
    # Configuration
    volumes:
      - /opt/ryokan-checker/config.json:/app/config.json:ro
      - /opt/ryokan-checker/logs:/app/logs
      - /tmp:/tmp
    
    environment:
      - CONFIG_PATH=/app/config.json
      - LOG_LEVEL=INFO
    
    # Networking
    networks:
      - production-network
    
    # Health checks
    healthcheck:
      test: ["CMD", "python", "-c", "import asyncio; import sys; sys.path.insert(0, '/app/src'); from main import AccommodationChecker; from config import load_config; asyncio.run(AccommodationChecker(load_config()).health_check())"]
      interval: 60s
      timeout: 15s
      retries: 3
      start_period: 60s
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

networks:
  production-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Deployment Process

### 1. Server Preparation

```bash
# Create application directory
sudo mkdir -p /opt/ryokan-checker/{config,logs}

# Set ownership
sudo chown -R 1000:1000 /opt/ryokan-checker

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Application Deployment

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/yourorg/ryokan-checker.git
cd ryokan-checker

# Copy production config
sudo cp config.example.json /opt/ryokan-checker/config/config.json
sudo nano /opt/ryokan-checker/config/config.json  # Edit with production values

# Build and deploy
sudo docker compose -f docker-compose.prod.yml build
sudo docker compose -f docker-compose.prod.yml up -d

# Verify deployment
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=50
```

### 3. Verification

```bash
# Check service health
curl -f http://localhost:8080/health

# Verify logs
sudo docker logs ryokan-checker-prod | tail -20

# Test notification endpoint
sudo docker compose exec accommodation-checker python -c "
import asyncio
from notifications import NotificationClient
client = NotificationClient('https://your-webhook.com/notify')
print(asyncio.run(client.test_endpoint()))
"
```

## Monitoring Setup

### Log Management

#### Log Rotation
```yaml
services:
  accommodation-checker:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
        compress: "true"
```

#### Log Aggregation (ELK Stack)
```yaml
services:
  accommodation-checker:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "fluentd-server:24224"
        fluentd-async-connect: "true"
        tag: "accommodation-checker.{{.Name}}"
```

### Metrics Collection

#### Prometheus Integration
```yaml
services:
  accommodation-checker:
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=8080"
      - "prometheus.io/path=/metrics"
    environment:
      - ENABLE_METRICS=true
```

#### Health Check Monitoring
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8080/health > /dev/null || echo "Service unhealthy" | mail admin@company.com
```

### Alerting Rules

#### Service Down Alert
```yaml
# Prometheus AlertManager
groups:
- name: accommodation-checker
  rules:
  - alert: ServiceDown
    expr: up{job="accommodation-checker"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Accommodation checker service is down"
```

#### No Availability Found (Extended Period)
```yaml
- alert: NoAvailabilityFound
  expr: time() - last_availability_found_timestamp > 86400
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "No availability found for 24+ hours"
```

## Security Hardening

### Container Security

```yaml
services:
  accommodation-checker:
    # Run as non-root user
    user: "1000:1000"
    
    # Security options
    security_opt:
      - no-new-privileges:true
      - apparmor:docker-default
      - seccomp:default
    
    # Drop all capabilities
    cap_drop:
      - ALL
    
    # Read-only filesystem
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
      - /var/tmp:noexec,nosuid,size=10m
    
    # Resource limits
    ulimits:
      nofile: 65536
      nproc: 4096
```

### Network Security

```yaml
networks:
  production-network:
    driver: bridge
    internal: true  # No external access
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  accommodation-checker:
    networks:
      production-network:
        ipv4_address: 172.20.0.10
```

### Firewall Configuration

```bash
# UFW rules
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 8080/tcp     # Block health check from external
sudo ufw enable
```

## High Availability Setup

### Multi-Instance Deployment

```yaml
services:
  accommodation-checker-1:
    <<: *accommodation-checker-base
    container_name: ryokan-checker-1
    environment:
      - INSTANCE_ID=1
      - CHECK_INTERVAL_OFFSET=0
  
  accommodation-checker-2:
    <<: *accommodation-checker-base
    container_name: ryokan-checker-2
    environment:
      - INSTANCE_ID=2
      - CHECK_INTERVAL_OFFSET=150  # 2.5 minute offset
```

### Load Balancer Configuration

```nginx
upstream accommodation-checkers {
    server 172.20.0.10:8080 weight=1 max_fails=3 fail_timeout=30s;
    server 172.20.0.11:8080 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name health-check.internal;
    
    location /health {
        proxy_pass http://accommodation-checkers;
        proxy_next_upstream error timeout http_500;
    }
}
```

## Backup Strategy

### Configuration Backup

```bash
#!/bin/bash
# /etc/cron.daily/ryokan-checker-backup

BACKUP_DIR="/opt/backups/ryokan-checker"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp /opt/ryokan-checker/config/config.json $BACKUP_DIR/config_$DATE.json

# Backup logs (last 7 days)
docker logs ryokan-checker-prod --since="168h" > $BACKUP_DIR/logs_$DATE.txt

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.json" -mtime +30 -delete
find $BACKUP_DIR -name "*.txt" -mtime +30 -delete
```

### Disaster Recovery

```bash
# Full system restore procedure
# 1. Restore configuration
cp /opt/backups/ryokan-checker/config_latest.json /opt/ryokan-checker/config/config.json

# 2. Rebuild service
cd /opt/ryokan-checker
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# 3. Verify operation
docker compose -f docker-compose.prod.yml logs --tail=50
curl -f http://localhost:8080/health
```

## Performance Optimization

### Resource Optimization

```yaml
services:
  accommodation-checker:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
    
    # Browser optimization
    environment:
      - BROWSER_ARGS=--no-sandbox --disable-dev-shm-usage --disable-gpu
      - MEMORY_LIMIT=768m
```

### Caching Strategy

```yaml
volumes:
  browser-cache:
    driver: local
  
services:
  accommodation-checker:
    volumes:
      - browser-cache:/home/appuser/.cache/ms-playwright
```

## Maintenance Procedures

### Regular Maintenance

```bash
#!/bin/bash
# /etc/cron.weekly/ryokan-checker-maintenance

# Update application
cd /opt/ryokan-checker
git pull origin main

# Rebuild if changes
if [ -n "$(git diff HEAD~1 --name-only)" ]; then
    docker compose -f docker-compose.prod.yml build --no-cache
    docker compose -f docker-compose.prod.yml up -d
fi

# Clean up old images
docker image prune -f

# Rotate logs manually if needed
docker logs ryokan-checker-prod --since="24h" > /opt/ryokan-checker/logs/app-$(date +%Y%m%d).log
```

### Health Monitoring

```bash
#!/bin/bash
# /etc/cron.hourly/ryokan-checker-health

HEALTH_URL="http://localhost:8080/health"
ALERT_EMAIL="admin@company.com"

if ! curl -f -s $HEALTH_URL > /dev/null; then
    echo "Health check failed at $(date)" | mail -s "Ryokan Checker Alert" $ALERT_EMAIL
    
    # Attempt restart
    cd /opt/ryokan-checker
    docker compose -f docker-compose.prod.yml restart
fi
```

## Compliance & Governance

### Audit Logging

```yaml
services:
  accommodation-checker:
    logging:
      driver: "syslog"
      options:
        syslog-address: "udp://syslog-server:514"
        tag: "accommodation-checker"
        syslog-format: "rfc5424"
```

### Data Retention

- **Logs**: 90 days retention
- **Configuration History**: 1 year retention
- **Metrics**: 6 months retention
- **Audit Logs**: 7 years retention

### Access Control

```bash
# Restrict access to production config
sudo chown root:docker /opt/ryokan-checker/config/config.json
sudo chmod 640 /opt/ryokan-checker/config/config.json

# Log access
sudo auditctl -w /opt/ryokan-checker/config/config.json -p wa -k config-access
```

This production deployment guide ensures a secure, scalable, and maintainable deployment of the accommodation checker service.