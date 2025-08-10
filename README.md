# Gassho-zukuri Accommodation Tracker

Monitors traditional gassho-zukuri houses in Shirakawa-go for availability and sends email notifications.

## Quick Start

1. Clone the repo
2. Set environment variables in `.env`:
   ```
   MAILGUN_API_KEY=your-api-key
   MAILGUN_DOMAIN=your-domain
   NOTIFICATION_EMAIL=your-email
   ```
3. Edit `config.json` with your target dates
4. Run: `docker-compose up -d`

## Features

- Checks all gassho-zukuri accommodations every 5 minutes
- Sends beautiful HTML email with all available options
- Includes web dashboard at http://localhost:8000
- Supports Traefik for custom domains

## Configuration

Edit `config.json`:
- `target_dates`: Array of dates to check (YYYY-MM-DD format)
- `check_interval_seconds`: How often to check (default: 300)

## Dashboard

View status at http://localhost:8000 or use `docker-compose -f docker-compose.with-dashboard.yml up -d`