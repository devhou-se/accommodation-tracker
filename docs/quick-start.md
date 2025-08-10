# Quick Start Guide

Get the Japanese Accommodation Availability Checker running in under 5 minutes.

## Prerequisites

- Docker and Docker Compose
- OR Python 3.11+ with pip

## Option 1: Docker (Recommended)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd gassho-zukuri-checker
cp config.example.json config.json
```

### 2. Edit Configuration

Edit `config.json`:

```json
{
  "target_dates": ["2025-08-27", "2025-08-28", "2025-08-31"],
  "notification_endpoint": "https://your-webhook-url.com/notify",
  "log_level": "INFO",
  "check_interval_seconds": 300
}
```

### 3. Run the Service

```bash
# Start the service
docker compose up

# Run in background
docker compose up -d

# View logs
docker compose logs -f accommodation-checker
```

## Option 2: Python

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure and Run

```bash
export CONFIG_PATH=./config.json
python src/main.py
```

## Test the Service

### With Mock Notification Service

```bash
# Start mock notification server
docker compose -f docker-compose.final-test.yml up -d

# Test with Python service
python test_full_docker.py

# Check received notifications
curl http://localhost:8082/notifications
```

### Single Run Test

```bash
export SINGLE_RUN=true
python src/main.py
```

## What Happens Next?

1. **Service Starts**: Loads configuration and initializes browser
2. **Tests Notification**: Verifies your webhook endpoint works
3. **Checks Accommodations**: Monitors all 12 Gassho houses in Ogimachi
4. **Sends Alerts**: Posts notifications when availability is found
5. **Repeats**: Continues checking at configured intervals

## Expected Output

```
INFO:main: Starting accommodation checker service
INFO:main: Testing notification endpoint
INFO:notifications.client: Endpoint test successful
INFO:main: Starting availability check
INFO:scrapers.base: Found accommodations count=12
INFO:main: No availability found
INFO:main: Sleeping until next check interval_seconds=300
```

## Notification Format

When availability is found, you'll receive:

```json
{
  "accommodation_name": "Rihee",
  "available_dates": ["2025-08-27", "2025-08-28"],
  "link": "https://www6.489pro.com/asp/489/menu.asp?id=21560023",
  "location": "Ogimachi, Shirakawa-go",
  "discovered_at": "2025-08-06T12:47:38Z"
}
```

## Next Steps

- [Configuration Guide](./configuration.md) - Detailed configuration options
- [Docker Deployment](./docker-deployment.md) - Production Docker setup
- [Monitoring](./monitoring.md) - Setting up monitoring and alerting