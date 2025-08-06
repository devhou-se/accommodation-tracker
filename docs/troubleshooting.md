# Troubleshooting Guide

Common issues and solutions for the Japanese Accommodation Availability Checker.

## Configuration Issues

### Invalid Configuration File

**Error**: `Configuration validation failed: Invalid date format`

**Cause**: Date format not in YYYY-MM-DD format

**Solution**:
```json
{
  "target_dates": ["2025-08-27", "2025-08-28"],  // Correct format
  // NOT: ["27/08/2025", "Aug 27, 2025"]
}
```

### Environment Variable Issues

**Error**: `Configuration file not found: None`

**Cause**: CONFIG_PATH environment variable not set

**Solution**:
```bash
# Set environment variable
export CONFIG_PATH=./config.json

# Or use default location
cp config.json /app/config.json
```

### Network Configuration

**Error**: `Notification endpoint test failed`

**Cause**: Incorrect notification URL or unreachable endpoint

**Debug Steps**:
```bash
# Test endpoint manually
curl -X POST https://your-webhook.com/notify \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check network connectivity
ping your-webhook-domain.com
```

## Browser/Scraping Issues

### Playwright Installation

**Error**: `Executable doesn't exist at /path/to/chromium`

**Cause**: Playwright browsers not installed

**Solution**:
```bash
# Install Playwright browsers
python -m playwright install chromium

# Install system dependencies
python -m playwright install-deps
```

### Browser Launch Failures

**Error**: `Browser failed to launch`

**Cause**: Missing system dependencies or permissions

**Solution for Docker**:
```dockerfile
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk-bridge2.0-0 \
    libdrm2 libxkbcommon0 libgbm1
```

**Solution for Local**:
```bash
# Ubuntu/Debian
sudo apt-get install -y libnss3-dev libatk-bridge2.0-dev libdrm-dev

# macOS (if using local installation)
brew install --cask chromium
```

### Site Access Issues

**Error**: `Timeout 30000ms exceeded`

**Possible Causes**:
1. Network connectivity issues
2. Site is down or slow
3. Rate limiting/blocking

**Debugging**:
```python
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test site accessibility
curl -I https://shirakawa-go.gr.jp/en/stay/
```

**Solutions**:
```json
{
  "timeout_seconds": 60,  // Increase timeout
  "check_interval_seconds": 600  // Reduce frequency
}
```

### No Accommodations Found

**Error**: `Found accommodations count=0`

**Cause**: Site structure changed or page not loading

**Debug Steps**:
1. Run debug script:
```bash
echo "1" | python debug_scraper.py
```

2. Check site manually in browser
3. Enable debug logging to see page content

**Common Fixes**:
- Update CSS selectors in scraper
- Check if site requires JavaScript
- Verify search URL still works

## Docker Issues

### Container Build Failures

**Error**: `failed to solve: process "/bin/sh -c pip install...`

**Cause**: Network issues or package conflicts

**Solution**:
```bash
# Clean build
docker compose build --no-cache

# Check base image
docker pull python:3.11-slim
```

### Container Memory Issues

**Error**: `Container killed with exit code 137`

**Cause**: Out of memory (OOM killer)

**Solution**:
```yaml
services:
  accommodation-checker:
    deploy:
      resources:
        limits:
          memory: 1g
        reservations:
          memory: 512m
```

### Port Binding Issues

**Error**: `bind: address already in use`

**Cause**: Port already in use by another service

**Solutions**:
```bash
# Find process using port
lsof -i :8080

# Kill process or change port
docker compose -f docker-compose.yml up --force-recreate
```

### Health Check Failures

**Error**: `container is unhealthy`

**Debug Steps**:
```bash
# Check container logs
docker compose logs accommodation-checker

# Manual health check
docker compose exec accommodation-checker python -c "
import asyncio
from main import AccommodationChecker
from config import load_config
print(asyncio.run(AccommodationChecker(load_config()).health_check()))
"
```

## Notification Issues

### HTTP Connection Errors

**Error**: `aiohttp.ClientConnectorError: Cannot connect to host`

**Causes**:
1. Incorrect notification URL
2. Network connectivity issues
3. Firewall blocking outbound requests

**Debug**:
```bash
# Test from container
docker compose exec accommodation-checker curl https://your-webhook.com

# Check DNS resolution
nslookup your-webhook-domain.com
```

### Webhook Endpoint Issues

**Error**: `Notification endpoint returned error status_code=500`

**Cause**: Your webhook endpoint has an error

**Debug Your Webhook**:
```bash
# Test with curl
curl -X POST https://your-webhook.com/notify \
  -H "Content-Type: application/json" \
  -d '{
    "accommodation_name": "Test",
    "available_dates": ["2025-12-25"],
    "link": "https://example.com",
    "location": "Test Location",
    "discovered_at": "2025-08-06T12:00:00Z"
  }'
```

### SSL/TLS Issues

**Error**: `aiohttp.ClientConnectorCertificateError`

**Cause**: SSL certificate validation issues

**Temporary Fix** (not recommended for production):
```python
# In notification client, add SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

## Performance Issues

### Slow Scraping

**Symptoms**: Long delays between checks

**Causes**:
1. Network latency
2. Site performance issues  
3. Browser overhead

**Solutions**:
```json
{
  "timeout_seconds": 20,  // Reduce timeout
  "check_interval_seconds": 600  // Less frequent checks
}
```

### Memory Usage

**Symptoms**: Container memory keeps growing

**Debug**:
```bash
# Monitor memory usage
docker stats accommodation-checker

# Check browser processes
docker compose exec accommodation-checker ps aux
```

**Solutions**:
- Ensure proper browser cleanup
- Restart container periodically
- Add memory limits

### High CPU Usage

**Symptoms**: Constant high CPU usage

**Causes**:
1. Browser processes not terminating
2. Infinite loops in scraping logic
3. Too frequent checks

**Debug**:
```bash
# Check process tree
docker compose exec accommodation-checker ps -ef --forest

# Monitor CPU
docker stats --no-stream
```

## Site-Specific Issues

### Site Structure Changes

**Error**: `No reservation link found`

**Cause**: Website changed structure

**Investigation**:
1. Visit site manually
2. Check if reservation links still exist
3. Update CSS selectors if needed

**Temporary Fix**:
- Use broader selectors
- Add fallback selectors
- Enable debug logging to see page content

### Accommodation Unavailable

**Warning**: `No availability found accommodation=SomeName`

**Causes**:
1. Normal - no availability for target dates
2. Accommodation temporarily closed
3. Booking system maintenance

**Not an Error**: This is expected behavior when no rooms are available.

### New Accommodations

**Issue**: New accommodations not being checked

**Cause**: Scraper only finds accommodations on main search page

**Solution**: The scraper automatically finds all accommodations on the search results page. New accommodations should be detected automatically.

## Logging and Debugging

### Enable Debug Logging

```bash
# Environment variable
export LOG_LEVEL=DEBUG

# Configuration file
{
  "log_level": "DEBUG"
}
```

### Log Analysis

**Find specific errors**:
```bash
# Search for errors
docker compose logs accommodation-checker | grep ERROR

# Filter by accommodation
docker compose logs accommodation-checker | grep "accommodation=Rihee"

# Recent logs only
docker compose logs --tail=100 accommodation-checker
```

### Common Log Messages

**Normal Operation**:
```json
{"event": "Starting availability check", "target_dates": ["2025-08-27"]}
{"event": "Found accommodations", "count": 12}
{"event": "No availability found"}
```

**Error Indicators**:
```json
{"level": "error", "event": "Scraping error", "accommodation": "Name"}
{"level": "warning", "event": "No reservation link found"}
{"level": "error", "event": "Notification failed"}
```

## Emergency Procedures

### Service Not Responding

1. **Check container status**:
```bash
docker compose ps
```

2. **Restart service**:
```bash
docker compose restart accommodation-checker
```

3. **Full rebuild if needed**:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Complete Reset

```bash
# Stop everything
docker compose down --rmi all --volumes

# Clean up
docker system prune -a

# Rebuild from scratch
docker compose build --no-cache
docker compose up -d
```

### Data Recovery

**Configuration Backup**:
```bash
# Backup config
cp config.json config.backup.json

# Restore from example
cp config.example.json config.json
# Edit with your settings
```

## Getting Help

### Diagnostic Information

When reporting issues, include:

```bash
# System information
docker --version
docker compose --version
python --version

# Service status
docker compose ps
docker compose logs --tail=50 accommodation-checker

# Configuration (redact sensitive data)
cat config.json | sed 's/"notification_endpoint": ".*"/"notification_endpoint": "[REDACTED]"/'

# Resource usage
docker stats --no-stream
```

### Testing Specific Components

**Test configuration loading**:
```python
python -c "from config import load_config; print(load_config('./config.json'))"
```

**Test notification client**:
```python
python test_with_mock.py
```

**Test scraper**:
```python
python debug_scraper.py
```