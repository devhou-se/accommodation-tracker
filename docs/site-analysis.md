# Site Analysis Guide

Detailed analysis of the Shirakawa-go booking system and web scraping implementation.

## Target Website Structure

### Primary Booking Flow

The Shirakawa-go booking system uses a complex multi-domain architecture:

```
shirakawa-go.gr.jp → Individual Accommodation Pages → 489pro.com Booking System
```

## 1. Search Results Page

**URL**: `https://shirakawa-go.gr.jp/en/stay/?tag%5B%5D=1&category%5B%5D=3#refine`

### Page Structure
```html
<div class="accommodation-listing">
  <a href="./33/">
    <h5>Rihee</h5>
    <div class="description">...</div>
  </a>
</div>
```

### Scraping Strategy
```python
# Extract accommodation links
links = await page.locator('a[href^="./"]').all()
for link in links:
    href = await link.get_attribute('href')
    if re.match(r'^\./\d+/$', href):
        # Valid accommodation link
```

### Data Extracted
- Accommodation names from `<h5>` elements
- Relative URLs (converted to absolute)
- Location information (all are in Ogimachi)

## 2. Individual Accommodation Pages

**URL Pattern**: `https://shirakawa-go.gr.jp/en/stay/{number}/`

### Key Elements
```html
<a href="https://www6.489pro.com/asp/489/menu.asp?id=21560023&lan=ENG&kid=00156">
  Click here for reservations.
</a>
```

### Scraping Implementation
```python
reservation_selectors = [
    'a:has-text("Click here for reservations")',
    'a[href*="489pro.com"]',
    'a[href*="menu.asp"]'
]

for selector in reservation_selectors:
    element = page.locator(selector).first
    if await element.count() > 0:
        reservation_link = await element.get_attribute('href')
        break
```

## 3. External Booking System (489pro.com)

### Package List Page
**URL Pattern**: `https://www6.489pro.com/asp/489/menu.asp?id={id}&lan=ENG&kid=00156`

#### Structure Analysis
```html
<table class="availability-table">
  <tr>
    <td>Room type</td>
    <td><a href="calendar-url">calendar</a></td>
    <td class="availability">○</td> <!-- Available -->
    <td class="availability">×</td> <!-- Unavailable -->
  </tr>
</table>
```

### Calendar Pages
**URL Pattern**: `https://www6.489pro.com/asp/489/date.asp?id={id}&room={room}&plan={plan}...`

#### Availability Indicators
```html
<!-- Available Date -->
<td>
  <a href="booking-form-url">
    8/27 ○ JPY15,400
  </a>
</td>

<!-- Unavailable Date -->
<td>
  8/28 ×
</td>
```

## Availability Detection Logic

### Pattern Recognition

The service identifies availability using multiple indicators:

1. **Circle Symbol**: `○` (Unicode U+25CB)
2. **Clickable Link**: Presence of `<a>` tag
3. **Price Information**: `JPY{amount}` pattern
4. **Date Format**: `{month}/{day}` pattern

### Implementation
```python
# Find available dates with circle symbol and price
available_cells = await page.locator('a:has-text("○"):has-text("JPY")').all()

for cell in available_cells:
    cell_text = await cell.text_content()
    if cell_text and '○' in cell_text:
        # Extract date from cell text
        date_match = re.search(r'(\d+)/(\d+)', cell_text)
        if date_match:
            month, day = date_match.groups()
            # Convert to YYYY-MM-DD format
            formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
```

## Challenges & Solutions

### Challenge 1: Multi-Domain Navigation

**Problem**: Booking flow spans multiple domains
- Main site: `shirakawa-go.gr.jp`  
- Booking system: `www6.489pro.com`

**Solution**: Seamless cross-domain navigation
```python
# Navigate across domains
await page.goto(accommodation_url)  # Main site
reservation_link = await page.locator('a[href*="489pro"]').get_attribute('href')
await page.goto(reservation_link)  # External booking system
```

### Challenge 2: Dynamic Content Loading

**Problem**: Calendar content loaded via JavaScript

**Solution**: Wait for network idle state
```python
await page.goto(calendar_url)
await page.wait_for_load_state('networkidle')
```

### Challenge 3: Multiple Room Types

**Problem**: Each accommodation has multiple room types with separate calendars

**Solution**: Iterate through all calendar links
```python
calendar_links = await page.locator('a:has-text("calendar")').all()
for calendar_link in calendar_links:
    calendar_url = await calendar_link.get_attribute('href')
    room_dates = await self._check_calendar_page(page, calendar_url, target_dates)
    available_dates.update(room_dates)
```

### Challenge 4: Date Format Inconsistency

**Problem**: Calendar shows `M/D` format but config expects `YYYY-MM-DD`

**Solution**: Dynamic year detection and format normalization
```python
# Extract year from calendar context
year_text = await page.locator('text=/2025|2024/').first.text_content()
year = '2025'  # Default
if year_text:
    year_match = re.search(r'(202[4-9])', year_text)
    if year_match:
        year = year_match.group(1)

# Format as YYYY-MM-DD
formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
```

## Site-Specific Accommodations

### Currently Supported (12 Gassho Houses)

1. **Hisamatsu** - `/stay/3/`
2. **Rihee** - `/stay/33/` 
3. **Koemon** - `/stay/7/`
4. **Nodaniya** - `/stay/29/`
5. **Isaburo** - `/stay/36/`
6. **Bunroku** - `/stay/34/`
7. **Yokichi** - `/stay/4/`
8. **Kidoya** - `/stay/9/`
9. **Yoshiro** - `/stay/32/`
10. **Gensaku** - `/stay/35/`
11. **Furusato** - `/stay/30/`
12. **Wadaya** - `/stay/18/`

### Accommodation Status Patterns

#### Active Bookings
- Has "Click here for reservations" link
- Links to 489pro.com booking system
- Shows calendar availability

#### Inactive/Closed
- No reservation link present
- May show "temporarily closed" message
- Still listed but not bookable

## Rate Limiting & Respect

### Implemented Safeguards

```python
# Delay between requests
await asyncio.sleep(2)  # 2 seconds between accommodations

# Respectful user agent
headers = {'User-Agent': 'Ryokan-Checker/1.0'}

# Timeout handling
timeout = 30000  # 30 seconds
```

### Best Practices
- Maximum 1 request per 2 seconds
- Use realistic browser user agent
- Implement proper timeout handling
- Fail gracefully on rate limiting
- Log all requests for monitoring

## Error Patterns & Handling

### Common Error Scenarios

1. **Site Maintenance**
   - Status: HTTP 503
   - Action: Log and retry later

2. **Network Timeouts**
   - Status: Timeout exception
   - Action: Exponential backoff retry

3. **Structure Changes**
   - Status: Elements not found
   - Action: Log detailed error, continue with other sites

4. **Captcha/Bot Detection**
   - Status: Unusual page content
   - Action: Implement longer delays, rotate user agents

### Error Logging
```python
self.logger.error(
    "Scraping error",
    accommodation=accommodation_name,
    error=str(e),
    url=page.url,
    status_code=response.status if response else None
)
```

## Performance Optimization

### Browser Resource Management
```python
# Reuse browser context
self.context = await self.browser.new_context()

# Close individual pages
await page.close()

# Cleanup on exit
await self.browser.close()
```

### Memory Optimization
- Close pages after use
- Limit concurrent browser tabs
- Clean up browser cache periodically
- Monitor memory usage

### Network Optimization
- Connection reuse where possible
- Compress responses when available
- Cache static resources
- Minimize redundant requests

## Future Site Changes

### Monitoring Strategy
- Log all selector failures
- Track success/failure rates per site
- Alert on significant pattern changes
- Implement automated testing

### Adaptation Framework
```python
class SiteAdapter:
    def detect_structure_change(self) -> bool:
        # Detect if site structure changed
        pass
    
    def update_selectors(self) -> None:
        # Update CSS selectors based on new structure
        pass
```

This analysis provides the foundation for understanding and maintaining the web scraping functionality as the target sites evolve over time.