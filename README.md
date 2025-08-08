# Japanese Accommodation Availability Checker

An automated service that monitors Japanese accommodation booking sites for availability and sends notifications when target dates become available.

## Overview

This service specifically targets traditional Japanese accommodations (Gassho houses) in Shirakawa-go, which typically release availability monthly and require constant monitoring to secure bookings.

## Features

- **Automated Monitoring**: Continuous checking of accommodation availability
- **Smart Detection**: Identifies available dates using visual calendar indicators
- **HTTP Notifications**: Sends JSON alerts to configured endpoints
- **Web Status Dashboard**: Beautiful real-time monitoring interface 📊
- **Containerized**: Docker-ready for easy deployment
- **Resilient**: Handles site changes gracefully with detailed logging
- **Configurable**: JSON-based configuration with environment variable overrides
- **Historical Tracking**: SQLite database stores all check results and discoveries

## Quick Start

### Using Docker

1. Copy the example configuration:
```bash
cp config.example.json config.json
```

2. Edit `config.json` with your target dates and notification endpoint:
```json
{
  "target_dates": ["2025-08-27", "2025-08-28"],
  "notification_endpoint": "https://your-notification-service.com/notify",
  "log_level": "INFO"
}
```

3. Build and run with Docker:
```bash
docker build -t accommodation-checker .
docker run -v $(pwd)/config.json:/app/config.json accommodation-checker
```

### Using Python

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Configure and run:
```bash
export CONFIG_PATH=./config.json
python src/main.py
```

## Configuration

### Required Settings

- `target_dates`: Array of dates in YYYY-MM-DD format to monitor
- `notification_endpoint`: HTTP URL to send availability alerts

### Optional Settings

- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `check_interval_seconds`: Time between checks (default: 300)
- `retry_attempts`: Number of retry attempts for failed requests (default: 3)
- `timeout_seconds`: Request timeout in seconds (default: 30)

### Environment Variables

Override configuration values using environment variables:

- `CONFIG_PATH`: Path to configuration file
- `LOG_LEVEL`: Override log level
- `NOTIFICATION_ENDPOINT`: Override notification URL

## Notification Format

When availability is found, the service sends HTTP POST requests with this JSON payload:

```json
{
  "accommodation_name": "Rihee",
  "available_dates": ["2025-08-27", "2025-08-28"],
  "link": "https://www6.489pro.com/asp/489/menu.asp?id=21560023",
  "location": "Ogimachi, Shirakawa-go",
  "discovered_at": "2025-08-06T22:37:38Z",
  "price_info": null
}
```

## Docker Compose

For development and testing:

```bash
# Start the service with mock notification endpoint
docker-compose up

# View logs
docker-compose logs -f accommodation-checker
```

## Architecture

The service follows a multi-stage scraping approach:

1. **Search Results**: Extract accommodation list from main search page
2. **Individual Pages**: Visit each accommodation to get booking system links
3. **Booking System**: Navigate to external booking system
4. **Calendar Analysis**: Check availability calendars for target dates

## Health Monitoring

The service includes health check endpoints for container orchestration:

```bash
# Check service health
curl http://localhost:8080/health
```

## Logging

Structured JSON logging provides detailed operational insights:

- **INFO**: Successful checks, availability found/not found
- **WARNING**: Recoverable errors, site structure changes  
- **ERROR**: Failed checks, notification failures
- **DEBUG**: Detailed scraping steps and browser interactions

## Testing

Run tests to verify the scraper works correctly:

```bash
# Test accommodation list extraction
echo "1" | python debug_scraper.py

# Test single accommodation page
echo "2" | python debug_scraper.py

# Quick availability test
python quick_test.py
```

## Troubleshooting

### Common Issues

**No availability found**: Check that target dates are within the booking window (typically 1-2 months ahead)

**Connection timeouts**: Increase `timeout_seconds` in configuration

**Rate limiting**: The service includes delays between requests, but you may need to reduce check frequency

**Site changes**: Check logs for detailed error messages and update selectors if needed

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
```

This provides step-by-step scraping information for troubleshooting.

## Development

Project structure:
```
/
├── src/
│   ├── config/          # Configuration management
│   ├── scrapers/        # Web scraping logic
│   ├── notifications/   # HTTP notification client
│   └── main.py         # Main application entry point
├── tests/              # Test files
├── docker/             # Docker-related files
├── Dockerfile          # Container definition
└── docker-compose.yml  # Development environment
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational and personal use only. Please respect the terms of service of the monitored websites and use responsibly.

## Disclaimer

This service is designed to help users monitor accommodation availability. Users are responsible for:

- Respecting website terms of service
- Using appropriate check intervals to avoid overwhelming servers
- Ensuring notifications comply with their intended use
- Making actual bookings through official channels

The service does not make bookings automatically - it only monitors and notifies.