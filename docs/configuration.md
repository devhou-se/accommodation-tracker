# Configuration Guide

Complete guide to configuring the Japanese Accommodation Availability Checker.

## Configuration File

The service uses a JSON configuration file with strict validation.

### Example Configuration

```json
{
  "target_dates": ["2025-08-27", "2025-08-28", "2025-08-31"],
  "notification_endpoint": "https://your-webhook.com/notify",
  "log_level": "INFO",
  "check_interval_seconds": 300,
  "retry_attempts": 3,
  "timeout_seconds": 30
}
```

## Required Settings

### `target_dates` (Required)
- **Type**: Array of strings
- **Format**: `YYYY-MM-DD`
- **Description**: Dates to monitor for availability
- **Example**: `["2025-08-27", "2025-08-28"]`

### `notification_endpoint` (Required)
- **Type**: URL string
- **Description**: HTTP endpoint to receive notifications
- **Example**: `"https://hooks.slack.com/services/YOUR/WEBHOOK/URL"`

## Optional Settings

### `log_level`
- **Type**: String
- **Default**: `"INFO"`
- **Options**: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`
- **Description**: Logging verbosity level

### `check_interval_seconds`
- **Type**: Integer
- **Default**: `300`
- **Minimum**: `60`
- **Description**: Time between availability checks

### `retry_attempts`
- **Type**: Integer
- **Default**: `3`
- **Range**: `1-10`
- **Description**: Number of retry attempts for failed requests

### `timeout_seconds`
- **Type**: Integer
- **Default**: `30`
- **Range**: `5-300`
- **Description**: Request timeout in seconds

## Environment Variable Overrides

You can override configuration values using environment variables:

### `CONFIG_PATH`
- **Default**: `/app/config.json`
- **Description**: Path to configuration file
- **Example**: `export CONFIG_PATH=./my-config.json`

### `LOG_LEVEL`
- **Override**: `log_level`
- **Example**: `export LOG_LEVEL=DEBUG`

### `NOTIFICATION_ENDPOINT`
- **Override**: `notification_endpoint`  
- **Example**: `export NOTIFICATION_ENDPOINT=https://myapi.com/webhook`

### `SINGLE_RUN`
- **Type**: Boolean (`true`/`false`)
- **Default**: `false`
- **Description**: Run once and exit (useful for testing)
- **Example**: `export SINGLE_RUN=true`

## Docker Environment Variables

When running with Docker, set environment variables in `docker-compose.yml`:

```yaml
services:
  accommodation-checker:
    environment:
      - CONFIG_PATH=/app/config.json
      - LOG_LEVEL=INFO
      - NOTIFICATION_ENDPOINT=https://your-webhook.com
      - SINGLE_RUN=false
```

## Validation Rules

The configuration is validated on startup:

- **Date Format**: Must be valid `YYYY-MM-DD` format
- **URL Format**: Notification endpoint must be valid HTTP/HTTPS URL
- **Numeric Ranges**: All numeric values must be within specified ranges
- **Required Fields**: Missing required fields cause startup failure

## Configuration Examples

### Development/Testing
```json
{
  "target_dates": ["2025-12-25", "2025-12-26"],
  "notification_endpoint": "http://localhost:8080/webhook",
  "log_level": "DEBUG",
  "check_interval_seconds": 60,
  "timeout_seconds": 15
}
```

### Production
```json
{
  "target_dates": ["2025-03-15", "2025-03-16", "2025-03-17"],
  "notification_endpoint": "https://api.yourservice.com/accommodations/notify",
  "log_level": "INFO", 
  "check_interval_seconds": 300,
  "retry_attempts": 5,
  "timeout_seconds": 45
}
```

### High-Frequency Monitoring
```json
{
  "target_dates": ["2025-04-01"],
  "notification_endpoint": "https://urgent-notifications.com/webhook",
  "log_level": "WARNING",
  "check_interval_seconds": 120,
  "retry_attempts": 2,
  "timeout_seconds": 20
}
```

## Error Handling

### Configuration Errors
- **Invalid JSON**: Service fails to start with clear error message
- **Missing Required Fields**: Validation error with field name
- **Invalid Dates**: Shows which dates are invalid
- **Invalid URLs**: URL validation error

### Runtime Configuration
- Environment variable overrides are logged at startup
- Configuration changes require service restart
- Validation happens before service initialization

## Best Practices

### Date Selection
- Monitor 2-7 dates for optimal performance
- Choose dates 1-3 months in advance (typical booking window)
- Consider Japanese holidays and peak seasons

### Check Intervals
- **Frequent**: 120-300 seconds (high availability periods)
- **Normal**: 300-600 seconds (regular monitoring)  
- **Conservative**: 600-1800 seconds (low priority dates)

### Notification Endpoints
- Use HTTPS for security
- Implement proper error handling in your webhook
- Consider rate limiting on your endpoint
- Test with the mock notification service first

### Logging
- Use `INFO` for production monitoring
- Use `DEBUG` only for troubleshooting (verbose)
- Use `WARNING` to reduce log volume in stable environments