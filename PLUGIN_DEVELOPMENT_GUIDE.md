# Plugin Development Guide

This guide explains how to create new booking availability checking plugins for the Accommodation Tracker service.

## Overview

The plugin system allows you to extend the service to monitor booking availability on different websites. Each plugin implements a standardized interface for checking availability and returning structured results.

## Plugin Architecture

### Base Classes

All plugins must inherit from the base `BookingPlugin` class located in `src/plugins/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class BookingAvailability:
    """Represents booking availability for a specific accommodation/date"""
    date: str
    room_type: str
    status: str  # 'available', 'limited', 'fully_booked'
    price: Optional[str] = None
    booking_url: Optional[str] = None
    venue: Optional[str] = None

@dataclass
class CheckResult:
    """Result of checking availability"""
    plugin_name: str
    item_name: str  # Name of the item being tracked (accommodation, event, etc.)
    check_time: datetime
    availabilities: List[BookingAvailability]
    success: bool
    error_message: Optional[str] = None

class BookingPlugin(ABC):
    """Base class for booking availability checking plugins"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
    
    @abstractmethod
    async def check_availability(self) -> CheckResult:
        """Check booking availability and return results"""
        pass
    
    @abstractmethod
    def get_item_info(self) -> Dict:
        """Get basic information about the item being tracked"""
        pass

# Legacy aliases for backward compatibility
TicketAvailability = BookingAvailability
TicketPlugin = BookingPlugin
```

## Creating a New Plugin

### Step 1: Create Plugin File

Create a new Python file in `src/plugins/` directory:

```bash
touch src/plugins/my_venue_plugin.py
```

### Step 2: Implement Plugin Class

```python
import re
import requests
from typing import Dict, List
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from .base import BookingPlugin, BookingAvailability, CheckResult

class MyVenuePlugin(BookingPlugin):
    """Plugin for checking My Venue booking availability"""
    
    def __init__(self, config: Dict):
        super().__init__("my_venue", config)
        self.base_url = config.get("url", "https://example.com")
        self.item_id = config.get("item_id")
        
    async def check_availability(self) -> CheckResult:
        """Check booking availability for the item"""
        try:
            # Fetch the webpage
            soup = self._fetch_page(self.base_url)
            
            # Extract availability data
            availabilities = self._extract_availability_data(soup)
            
            return CheckResult(
                plugin_name=self.name,
                item_name=self.config.get("item_name", "Item"),
                check_time=datetime.now(timezone.utc),
                availabilities=availabilities,
                success=True
            )
            
        except Exception as e:
            return CheckResult(
                plugin_name=self.name,
                item_name=self.config.get("item_name", "Item"),
                check_time=datetime.now(timezone.utc),
                availabilities=[],
                success=False,
                error_message=str(e)
            )
    
    def _fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    
    def _extract_availability_data(self, soup: BeautifulSoup) -> List[BookingAvailability]:
        """Extract booking availability from the parsed HTML"""
        availabilities = []
        
        # TODO: Implement your website-specific parsing logic here
        # Example:
        booking_elements = soup.find_all('div', class_='booking-item')
        
        for element in booking_elements:
            room_type = element.find('span', class_='room-type').get_text(strip=True)
            status_element = element.find('span', class_='status')
            
            if 'available' in status_element.get('class'):
                status = 'available'
                booking_link = element.find('a', class_='book-button')
                booking_url = booking_link.get('href') if booking_link else None
            elif 'fully-booked' in status_element.get('class'):
                status = 'fully_booked'
                booking_url = None
            else:
                status = 'limited'
                booking_url = None
            
            availabilities.append(BookingAvailability(
                date="Booking date",
                room_type=room_type,
                status=status,
                booking_url=booking_url
            ))
        
        return availabilities
    
    def get_item_info(self) -> Dict:
        """Get basic item information"""
        return {
            "name": self.config.get("item_name", "Item"),
            "venue": self.config.get("venue", "Unknown"),
            "url": self.base_url,
            "item_id": self.item_id
        }
```

### Step 3: Register Plugin

Add your plugin to `src/plugins/__init__.py`:

```python
from .base import BookingPlugin, BookingAvailability, CheckResult, TicketPlugin, TicketAvailability
from .sumo_plugin import SumoPlugin
from .shirakawa_accommodation_plugin import ShirakawaAccommodationPlugin
from .direct_booking_plugin import DirectBookingPlugin
from .my_venue_plugin import MyVenuePlugin  # Add this import

# Plugin registry
AVAILABLE_PLUGINS = {
    "sumo": SumoPlugin,
    "shirakawa_accommodation": ShirakawaAccommodationPlugin,
    "direct_booking": DirectBookingPlugin,
    "my_venue": MyVenuePlugin  # Add this entry
}

def create_plugin(plugin_type: str, config: dict) -> BookingPlugin:
    """Factory function to create plugin instances"""
    if plugin_type not in AVAILABLE_PLUGINS:
        raise ValueError(f"Unknown plugin type: {plugin_type}")
    
    return AVAILABLE_PLUGINS[plugin_type](config)
```

### Step 4: Configure Plugin

Add your plugin configuration to `config.json`:

```json
{
  "email": {
    "api_key": "your-mailgun-api-key",
    "domain": "your-domain.com",
    "from_email": "tickets@your-domain.com",
    "recipients": ["user@example.com"]
  },
  "plugins": [
    {
      "type": "my_venue",
      "name": "my_event_checker",
      "enabled": true,
      "check_interval_minutes": 60,
      "config": {
        "url": "https://bookings.myvenue.com/accommodations/12345",
        "item_id": "12345",
        "item_name": "My Accommodation",
        "venue": "My Venue"
      }
    }
  ],
  "web_port": 8080,
  "log_level": "INFO"
}
```

## Plugin Development Best Practices

### 1. Web Scraping Guidelines

- **Use proper headers**: Always include a realistic User-Agent header
- **Respect rate limits**: Don't make requests too frequently
- **Handle errors gracefully**: Website structure can change
- **Use BeautifulSoup4**: Recommended for HTML parsing
- **Follow robots.txt**: Respect website scraping policies

### 2. Status Classification

Use these standard status values:

- **`available`**: Bookings can be made now
- **`limited`**: Few spots remaining
- **`fully_booked`**: No availability
- **`not_on_sale`**: Bookings not yet open
- **`unknown`**: Status could not be determined

### 3. URL Handling

```python
def _construct_url(self, href: str) -> str:
    """Construct absolute URL from relative path"""
    if href.startswith('http'):
        return href
    elif href.startswith('/'):
        # Absolute path
        base_parts = self.base_url.split('/')[:3]  # ['https:', '', 'domain.com']
        return '/'.join(base_parts) + href
    else:
        # Relative path
        return f"{self.base_url.rstrip('/')}/{href}"
```

### 4. Error Handling

```python
async def check_availability(self) -> CheckResult:
    try:
        # Main logic here
        pass
    except requests.RequestException as e:
        return CheckResult(
            plugin_name=self.name,
            item_name=self.item_name,
            check_time=datetime.now(timezone.utc),
            availabilities=[],
            success=False,
            error_message=f"Network error: {str(e)}"
        )
    except Exception as e:
        return CheckResult(
            plugin_name=self.name,
            item_name=self.item_name,
            check_time=datetime.now(timezone.utc),
            availabilities=[],
            success=False,
            error_message=f"Unexpected error: {str(e)}"
        )
```

### 5. Configuration Parameters

Common configuration parameters:

```json
{
  "type": "plugin_type",
  "name": "unique_instance_name",
  "enabled": true,
  "check_interval_minutes": 30,
  "config": {
    "url": "https://venue.com/accommodation",
    "item_id": "12345",
    "item_name": "Accommodation Name",
    "venue": "Venue Name",
    "custom_param": "value"
  }
}
```

## Testing Your Plugin

### 1. Unit Testing

Create a test file for your plugin:

```python
# tests/test_my_venue_plugin.py
import pytest
from src.plugins.my_venue_plugin import MyVenuePlugin

def test_plugin_initialization():
    config = {
        "url": "https://example.com",
        "item_id": "123"
    }
    plugin = MyVenuePlugin(config)
    assert plugin.name == "my_venue"
    assert plugin.base_url == "https://example.com"

async def test_check_availability():
    config = {"url": "https://example.com", "item_name": "Test Accommodation"}
    plugin = MyVenuePlugin(config)
    
    # Mock the _fetch_page method for testing
    # result = await plugin.check_availability()
    # assert result.success is True
```

### 2. Single Run Testing

Test your plugin in isolation:

```bash
# Create test config
echo '{
  "email": {"api_key": "", "domain": "", "from_email": "", "recipients": []},
  "plugins": [{
    "type": "my_venue",
    "name": "test_instance",
    "enabled": true,
    "check_interval_minutes": 60,
    "config": {
      "url": "https://venue.com/accommodation",
      "item_name": "Test Accommodation"
    }
  }],
  "web_port": 8080,
  "log_level": "DEBUG"
}' > config.test.json

# Run single check
CONFIG_PATH=config.test.json SINGLE_RUN=true python3 -m src.main
```

### 3. Web Dashboard Testing

Start the service and test via the web interface:

```bash
CONFIG_PATH=config.test.json python3 -m src.main
```

Then visit `http://localhost:8080` and use the "Check Now" button.

## Common Integration Patterns

### 1. Multi-Event Support

For venues with multiple events:

```python
class MultiEventPlugin(TicketPlugin):
    def __init__(self, config: Dict):
        super().__init__("multi_event", config)
        self.events = config.get("events", [])
    
    async def check_availability(self) -> CheckResult:
        all_availabilities = []
        
        for event in self.events:
            event_availabilities = await self._check_single_event(event)
            all_availabilities.extend(event_availabilities)
        
        return CheckResult(
            plugin_name=self.name,
            item_name="Multiple Items",
            check_time=datetime.now(timezone.utc),
            availabilities=all_availabilities,
            success=True
        )
```

### 2. API-Based Plugins

For venues with APIs:

```python
async def check_availability(self) -> CheckResult:
    try:
        headers = {
            'Authorization': f'Bearer {self.config.get("api_token")}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f"{self.api_base}/accommodations/{self.item_id}/availability",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        availabilities = self._parse_api_response(data)
        
        return CheckResult(
            plugin_name=self.name,
            item_name=data.get('item_name', 'Item'),
            check_time=datetime.now(timezone.utc),
            availabilities=availabilities,
            success=True
        )
    except Exception as e:
        # Handle errors...
```

### 3. Date-Specific Plugins

For events with multiple dates:

```python
def _extract_availability_data(self, soup: BeautifulSoup) -> List[TicketAvailability]:
    availabilities = []
    
    date_sections = soup.find_all('div', class_='date-section')
    for section in date_sections:
        date_str = section.find('h3').get_text(strip=True)
        booking_types = section.find_all('div', class_='booking-type')
        
        for booking in booking_types:
            room_type = booking.find('span', class_='type').get_text(strip=True)
            status = self._determine_status(booking)
            
            availabilities.append(BookingAvailability(
                date=date_str,
                room_type=room_type,
                status=status,
                booking_url=self._extract_booking_url(booking) if status == 'available' else None
            ))
    
    return availabilities
```

## Troubleshooting

### Common Issues

1. **Website Structure Changes**: Websites frequently update their HTML structure
   - Solution: Make selectors flexible and add fallback logic

2. **Rate Limiting**: Too many requests can get blocked
   - Solution: Increase check intervals, add delays between requests

3. **JavaScript-Rendered Content**: Some sites load content dynamically
   - Solution: Look for API endpoints or consider using Selenium for complex cases

4. **Anti-Bot Measures**: Websites may block automated requests
   - Solution: Rotate User-Agent headers, use proper headers, respect robots.txt

### Debugging Tips

1. **Enable debug logging**:
   ```json
   {"log_level": "DEBUG"}
   ```

2. **Save HTML for inspection**:
   ```python
   def _fetch_page(self, url: str) -> BeautifulSoup:
       response = requests.get(url, headers=self.headers, timeout=30)
       
       # Save for debugging
       with open('/tmp/debug_page.html', 'w') as f:
           f.write(response.text)
       
       return BeautifulSoup(response.content, 'html.parser')
   ```

3. **Test URL construction**:
   ```python
   print(f"Constructed URL: {self._construct_url(relative_path)}")
   ```

## Security Considerations

1. **Never hardcode credentials**: Use configuration files
2. **Validate inputs**: Sanitize all user-provided configuration
3. **Handle sensitive data**: Don't log booking URLs or personal information
4. **Use HTTPS**: Always prefer secure connections
5. **Respect privacy**: Only collect publicly available information

## Performance Optimization

1. **Cache responses**: For data that doesn't change frequently
2. **Parallel requests**: For multiple events/dates
3. **Efficient parsing**: Use specific selectors instead of searching entire documents
4. **Minimize requests**: Combine multiple checks where possible

## Plugin Lifecycle

1. **Development**: Create and test your plugin
2. **Integration**: Add to plugin registry and configuration
3. **Deployment**: Update Docker image and restart service
4. **Monitoring**: Watch logs and dashboard for errors
5. **Maintenance**: Update selectors when websites change

Remember to always respect the website's terms of service and robots.txt file when developing plugins.