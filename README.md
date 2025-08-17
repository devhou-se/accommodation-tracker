# Accommodation Tracker 🏠🤖

An automated booking availability monitor that tracks accommodation availability and event tickets (Japanese traditional guesthouses, Sumo tournaments) and sends email notifications when availability is found.

## Features

- **Plugin Architecture**: Easily add support for different booking websites and event systems
- **Multi-Type Monitoring**: Supports both accommodation booking and event ticket tracking
- **Direct Booking Integration**: Targets specific booking URLs using Playwright automation
- **Email Notifications**: Mailgun integration for email alerts  
- **Web Dashboard**: Real-time status monitoring and manual checks
- **Configurable Scheduling**: Set custom check intervals per plugin
- **Docker Support**: Fully containerized service with Playwright browser support

## Supported Systems

- **489pro.com**: Japanese accommodation booking system (Shirakawa-go traditional houses)
- **Direct Booking Plugin**: Generic plugin for direct booking page monitoring
- **Sumo Plugin**: Japanese Sumo tournament ticket availability monitoring

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <this-repo>
   cd accommodation-tracker
   ```

2. **Create Configuration**
   ```bash
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

3. **Run with Docker (Recommended)**
   ```bash
   docker-compose up --build
   ```

4. **Access Dashboard**
    - Open http://localhost:8080 in your browser

## Configuration

### Example Configuration

Edit `config.json` to configure the service:

```json
{
  "email": {
    "enabled": true,
    "provider": "mailgun",
    "config": {
      "domain": "mg.yourdomain.com",
      "api_key": "your-mailgun-api-key",
      "from_email": "noreply@mg.yourdomain.com",
      "to_email": "your-email@example.com"
    }
  },
  "plugins": [
    {
      "type": "direct_booking",
      "name": "shirakawa_accommodations",
      "enabled": true,
      "check_interval_minutes": 60,
      "config": {
        "booking_urls": [
          "https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156",
          "https://www6.489pro.com/asp/489/menu.asp?id=21560023&lan=ENG&kid=00156"
        ],
        "target_dates": ["2025-11-04"]
      }
    },
    {
      "type": "sumo",
      "name": "sumo_november_2025",
      "enabled": true,
      "check_interval_minutes": 60,
      "config": {
        "url": "https://sumo.pia.jp/en/",
        "tournament_month": "11",
        "year": "2025"
      }
    }
  ],
  "web_port": 8080,
  "log_level": "INFO"
}
```

### Email Configuration

Email configuration is simplified - only domain and from_email are required:

- **domain**: Your email domain (e.g., "mail.example.com")
- **from_email**: Sender email address (e.g., "bot@mail.example.com")

### Plugin Configuration

#### Direct Booking Plugin

The `direct_booking` plugin monitors specific booking URLs for room availability:

- **booking_urls**: Array of direct booking page URLs to monitor
- **target_dates**: Array of dates to check (YYYY-MM-DD format)

#### Sumo Plugin

The `sumo` plugin monitors Japanese Sumo tournament ticket availability:

- **url**: Base URL for the sumo ticket site (e.g., "https://sumo.pia.jp/en/")
- **tournament_month**: Month of the tournament ("01", "03", "05", "07", "09", "11")
- **year**: Tournament year (e.g., "2025")

## Development

### Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Run single check (testing)**
   ```bash
   CONFIG_PATH=config.json SINGLE_RUN=true python -m src.main
   ```

3. **Run service**
   ```bash
   CONFIG_PATH=config.json python -m src.main
   ```

### Adding New Plugins

1. Create a new plugin in `src/plugins/`
2. Extend the `BookingPlugin` base class
3. Implement `check_availability()` and `get_item_info()` methods
4. Register in `src/plugins/__init__.py`

Example plugin structure:
```python
from .base import BookingPlugin, CheckResult, BookingAvailability

class MyPlugin(BookingPlugin):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("my_plugin", config)
        
    async def check_availability(self) -> CheckResult:
        # Implement availability checking logic
        availabilities = []
        # ... your logic here
        
        return CheckResult(
            plugin_name=self.name,
            item_name="My Item",
            check_time=datetime.now(),
            availabilities=availabilities,
            success=True
        )

    def get_item_info(self) -> Dict:
        return {
            "name": "My Item",
            "dates": ["2025-11-04"],
            "venues": ["Location 1"]
        }
```

## API Endpoints

- `GET /` - Web dashboard
- `GET /api/status` - Service status
- `GET /api/results` - Recent check results
- `POST /api/check/{plugin_name}` - Manual check for specific plugin
- `POST /api/check-all` - Manual check for all plugins
- `GET /health` - Health check

## Docker

### Build Image
```bash
docker build -t slop-bot .
```

### Run Container
```bash
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/config.json:/app/config.json:ro \
  -v $(pwd)/data:/app/data \
  slop-bot
```

### Using Docker Compose
```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## Environment Variables

- `CONFIG_PATH`: Path to configuration file (default: `config.json`)
- `SINGLE_RUN`: Set to `true` for one-time check mode
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Common Issues

1. **Playwright browser not found**
   ```bash
   playwright install chromium
   ```

2. **Permission denied on data directory**
   ```bash
   chmod 755 data/
   ```

3. **Mailgun authentication failed**
    - Verify API key and domain in config
    - Check Mailgun account status

4. **Browser crashes in Docker**
    - Ensure sufficient memory allocation (at least 2GB recommended)
    - Add `--no-sandbox --disable-dev-shm-usage` flags if needed

### Configuration Files

Configuration is managed through `config.json`. A sample configuration is available in `deploy/config.json`.

### Logs

View application logs:
```bash
# Docker Compose
docker-compose logs -f slop-bot

# Docker
docker logs -f <container-id>

# Local development
tail -f accommodation_log_*.json
```

## How It Works

1. **Direct URL Targeting**: Reads booking URLs directly instead of crawling
2. **JavaScript Handling**: Uses Playwright to interact with dynamic booking calendars
3. **Smart Navigation**: Automatically navigates through calendar weeks to find target dates
4. **Room Detection**: Extracts room types and availability from booking table structures
5. **Clean Output**: Formats results in user-friendly format with pricing information

## Example Output

```
🏠 Accommodation Tracker - Multi-purpose Availability Monitor 🤖
Plugin: direct_booking
Check time: 2025-08-17 11:14:43
Success: True
Booking Availability Found:
  ✅ 8 Japanese Tatami mats (Oct-Nov 2025 Package): available
    Price: JPY17,050
    Booking URL: https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156
  ✅ 12 Japanese Tatami mats (Oct-Nov 2025 Package): available  
    Price: JPY19,250
    Booking URL: https://www6.489pro.com/asp/489/menu.asp?id=21560019&lan=ENG&kid=00156

Plugin: sumo
Check time: 2025-08-17 11:15:02
Success: True
Ticket Availability Found:
  ✅ 2025 November Grand Tournament: available
    Venue: Fukuoka
    Tickets available for purchase
    Booking URL: https://sumo.pia.jp/en/
```

## License

MIT License