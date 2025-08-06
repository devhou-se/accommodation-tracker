# API Reference

Complete reference for the Japanese Accommodation Availability Checker codebase.

## Configuration Module (`src/config/`)

### `Config` Class

**File**: `src/config/schema.py`

```python
class Config(BaseModel):
    target_dates: List[str]
    notification_endpoint: HttpUrl
    log_level: str = "INFO"
    check_interval_seconds: int = 300
    retry_attempts: int = 3
    timeout_seconds: int = 30
```

#### Fields

- **`target_dates`**: List of dates in YYYY-MM-DD format to monitor
- **`notification_endpoint`**: HTTP URL for sending notifications
- **`log_level`**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **`check_interval_seconds`**: Time between availability checks (min: 60)
- **`retry_attempts`**: Number of retry attempts for failed requests (1-10)
- **`timeout_seconds`**: Request timeout in seconds (5-300)

#### Validators

```python
@field_validator('target_dates')
@classmethod
def validate_dates(cls, v):
    # Validates YYYY-MM-DD format and date validity
```

### `load_config()` Function

**File**: `src/config/loader.py`

```python
def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from JSON file with environment variable overrides."""
```

#### Parameters
- **`config_path`**: Path to JSON config file (default: from CONFIG_PATH env var)

#### Returns
- **`Config`**: Validated configuration object

#### Raises
- **`FileNotFoundError`**: Config file not found
- **`ValueError`**: Invalid JSON or validation error

## Scraper Module (`src/scrapers/`)

### `AccommodationResult` Class

**File**: `src/scrapers/base.py`

```python
@dataclass
class AccommodationResult:
    accommodation_name: str
    available_dates: List[str]
    link: str
    location: str
    price_info: Optional[str] = None
    discovered_at: Optional[str] = None
```

#### Fields

- **`accommodation_name`**: Name of the accommodation
- **`available_dates`**: List of available dates (YYYY-MM-DD format)
- **`link`**: URL to booking page
- **`location`**: Location description
- **`price_info`**: Price information (if available)
- **`discovered_at`**: ISO timestamp when availability was found

### `BaseScraper` Abstract Class

**File**: `src/scrapers/base.py`

```python
class BaseScraper(ABC):
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
```

#### Abstract Methods

```python
async def check_availability(self, target_dates: List[str]) -> List[AccommodationResult]:
    """Check availability for the given dates."""

async def cleanup(self):
    """Clean up any resources (browser instances, etc.)."""
```

#### Utility Methods

```python
def filter_available_dates(self, target_dates: List[str], available_dates: List[str]) -> List[str]:
    """Filter available dates to only include target dates."""

def log_availability_found(self, accommodation_name: str, dates: List[str]):
    """Log when availability is found."""

def log_no_availability(self, accommodation_name: str):
    """Log when no availability is found."""

def log_scraping_error(self, accommodation_name: str, error: str):
    """Log scraping errors."""
```

### `ShirakawaScraper` Class

**File**: `src/scrapers/shirakawa_scraper.py`

```python
class ShirakawaScraper(BaseScraper):
    SEARCH_URL = "https://shirakawa-go.gr.jp/en/stay/?tag%5B%5D=1&category%5B%5D=3#refine"
    
    def __init__(self, timeout_seconds: int = 30):
        super().__init__(timeout_seconds)
```

#### Public Methods

```python
async def check_availability(self, target_dates: List[str]) -> List[AccommodationResult]:
    """Check availability for all Gassho houses in Ogimachi area."""
```

#### Private Methods

```python
async def _initialize_browser(self):
    """Initialize Playwright browser."""

async def _get_accommodation_list(self) -> List[Dict[str, str]]:
    """Extract accommodation list from the search results page."""

async def _check_single_accommodation(self, acc_info: Dict[str, str], target_dates: List[str]) -> Optional[AccommodationResult]:
    """Check availability for a single accommodation."""

async def _check_calendar_page(self, page: Page, calendar_url: str, target_dates: List[str]) -> List[str]:
    """Check a specific calendar page for availability."""
```

## Notification Module (`src/notifications/`)

### `NotificationClient` Class

**File**: `src/notifications/client.py`

```python
class NotificationClient:
    def __init__(self, endpoint_url: str, timeout_seconds: int = 30, retry_attempts: int = 3):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
```

#### Public Methods

```python
async def send_notification(self, result: AccommodationResult) -> bool:
    """Send a notification for an accommodation availability result."""

async def send_notifications(self, results: List[AccommodationResult]) -> int:
    """Send notifications for multiple results."""

async def test_endpoint(self) -> bool:
    """Test the notification endpoint with a dummy payload."""
```

#### Private Methods

```python
def _build_payload(self, result: AccommodationResult) -> dict:
    """Build notification payload matching the expected format."""

async def _send_http_notification(self, payload: dict) -> bool:
    """Send HTTP POST notification to the configured endpoint."""
```

## Main Application (`src/main.py`)

### `AccommodationChecker` Class

```python
class AccommodationChecker:
    def __init__(self, config: Config):
        self.config = config
        self.running = True
        self.scraper = None
        self.notification_client = None
```

#### Public Methods

```python
async def start(self, single_run: bool = False):
    """Start the accommodation checking service."""

async def health_check(self) -> dict:
    """Perform health check and return status."""

async def cleanup(self):
    """Clean up resources."""
```

#### Private Methods

```python
async def _check_availability(self):
    """Perform a single availability check cycle."""

def _setup_signal_handlers(self):
    """Set up signal handlers for graceful shutdown."""
```

### `main()` Function

```python
async def main():
    """Main entry point."""
```

## Environment Variables

### Configuration Overrides

- **`CONFIG_PATH`**: Path to configuration file (default: `/app/config.json`)
- **`LOG_LEVEL`**: Override log level
- **`NOTIFICATION_ENDPOINT`**: Override notification URL
- **`SINGLE_RUN`**: Run once and exit (`true`/`false`)

## Notification Payload Format

### Request Format

```json
POST /notify HTTP/1.1
Content-Type: application/json
User-Agent: Ryokan-Checker/1.0

{
  "accommodation_name": "Rihee",
  "available_dates": ["2025-08-27", "2025-08-28"],
  "link": "https://www6.489pro.com/asp/489/menu.asp?id=21560023",
  "location": "Ogimachi, Shirakawa-go",
  "discovered_at": "2025-08-06T12:47:38Z",
  "price_info": null
}
```

### Response Format

```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "message": "Notification received"
}
```

## Health Check Endpoint

### Request

```http
GET /health HTTP/1.1
```

### Response

```json
{
  "status": "healthy",
  "target_dates": ["2025-08-27", "2025-08-28"],
  "check_interval": 300,
  "notification_endpoint": "https://example.com/notify"
}
```

## Logging Format

### Structured JSON Logging

```json
{
  "timestamp": "2025-08-06T12:47:38.266588Z",
  "level": "info",
  "logger": "scrapers.base",
  "event": "Availability found",
  "accommodation": "Rihee",
  "dates": ["2025-08-27", "2025-08-28"],
  "date_count": 2,
  "scraper": "ShirakawaScraper"
}
```

### Log Levels

- **DEBUG**: Detailed scraping steps and browser interactions
- **INFO**: Successful checks, availability found/not found
- **WARNING**: Recoverable errors, site structure changes
- **ERROR**: Failed checks, notification failures

## Error Handling

### Exception Hierarchy

```python
# Base exceptions
class ConfigurationError(Exception):
    """Configuration validation or loading errors."""

class ScrapingError(Exception):
    """Web scraping related errors."""

class NotificationError(Exception):
    """Notification sending errors."""
```

### Common Error Scenarios

#### Configuration Errors
- Invalid JSON format
- Missing required fields
- Invalid date formats
- Invalid URL formats

#### Scraping Errors
- Network timeouts
- Site structure changes
- Rate limiting
- Browser initialization failures

#### Notification Errors
- HTTP connection failures
- Invalid response status
- Endpoint unavailable
- Request timeouts

## Browser Automation Details

### Playwright Configuration

```python
# Browser launch options
browser = await playwright.chromium.launch(
    headless=True,
    args=['--no-sandbox', '--disable-dev-shm-usage']
)

# Context configuration
context = await browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
)
```

### Page Interaction Patterns

```python
# Wait for page load
await page.goto(url, timeout=30000)
await page.wait_for_load_state('networkidle')

# Element interaction
element = page.locator('selector')
if await element.count() > 0:
    text = await element.text_content()
    href = await element.get_attribute('href')
```

## Testing Framework

### Test Utilities

```python
# Debug accommodation list
async def debug_accommodation_list():
    scraper = ShirakawaScraper()
    accommodations = await scraper._get_accommodation_list()

# Test single accommodation
async def test_single_accommodation():
    acc_info = {'name': 'Rihee', 'url': 'https://...'}
    result = await scraper._check_single_accommodation(acc_info, dates)
```

### Mock Services

```python
# Mock notification service (Node.js/Express)
app.post('/notify', (req, res) => {
  console.log('Notification received:', req.body);
  res.json({status: 'success'});
});
```