# Japanese Accommodation Availability Checker

## Problem Statement

Booking sites for traditional Japanese accommodations are generally archaic with non-intuitive interfaces. Availability for these accommodations is typically released on a monthly basis for the month ahead, making it extremely difficult to secure bookings without constant manual monitoring.

The only reliable way to successfully make a booking is to regularly check the sites for availability on intended dates, which is time-consuming and often unsuccessful due to the unpredictable nature of availability releases.

## Solution Overview

An automated service that monitors Japanese accommodation booking sites for availability and sends notifications when target dates become available. The service will be containerized and run on a scheduled basis via external cron jobs to continuously monitor specified accommodations.

## Functional Requirements

### 1. Availability Checking
- **Website Monitoring**: Scrape the Shirakawa-go booking site (hard-coded URLs)
- **Calendar Parsing**: Detect availability indicators on calendar pages (circles, green indicators, etc.)
- **Site Analysis**: Analyze site structure programmatically to understand data patterns
- **Date Range Checking**: Monitor specific date ranges as configured
- **Location Filtering**: Filter results by Ogimachi area in Shirakawa-go

### 2. Notification System
- **HTTP Notifications**: POST availability alerts to notification endpoint
- **Payload Structure**: Include accommodation details, dates, and booking links
- **Error Handling**: Retry failed notifications with exponential backoff
- **Rate Limiting**: Respect notification service limits

### 3. Configuration Management
- **JSON Configuration**: Load settings from `config.json` file
- **Schema Validation**: Validate configuration on startup
- **Hot Reloading**: Support configuration updates without restart (if possible)
- **Environment Overrides**: Allow environment variables to override config values

## Technical Requirements

### Core Technologies
- **Language**: Python or Go
- **Web Automation**: Browser automation tools for web scraping
- **Containerization**: Docker with multi-stage builds
- **Configuration**: JSON-based with schema validation

### Operational Requirements
- **Logging**: Structured logging (JSON format) with configurable levels
- **Health Checks**: HTTP endpoint for container health monitoring
- **Graceful Shutdown**: Handle SIGTERM/SIGINT properly
- **Error Recovery**: Automatic retry with exponential backoff
- **Rate Limiting**: Configurable delays between requests to avoid being blocked

### Performance & Reliability
- **Headless Operation**: Run browser in headless mode for efficiency
- **Resource Management**: Proper cleanup of browser instances
- **Timeout Handling**: Configurable timeouts for page loads and interactions
- **Failure Isolation**: Continue checking other sites if one fails

## Site-Specific Implementation Details

### Shirakawa-go Booking System (Hard-coded URLs)

**Root Search Page**:
- URL: `https://shirakawa-go.gr.jp/en/stay/?tag%5B%5D=1&category%5B%5D=3#refine` (hard-coded)
- Purpose: Search for Gassho houses in Ogimachi area
- Implementation: Use Playwright to analyze page structure and extract listing URLs programmatically

**Listing Page Example**:
- URL: `https://shirakawa-go.gr.jp/en/stay/3/` (discovered programmatically)
- Purpose: Individual accommodation details and booking link
- Implementation: Use Playwright to understand page structure and extract accommodation names and calendar links

**Calendar Page Example**:
- URL: `https://www6.489pro.com/asp/489/date.asp?id=21560022&room=3&plan=145&meo=&lan=ENG&kid=00156&key=&m_menu=1`
- Implementation: Use Playwright to analyze calendar structure and detect availability indicators programmatically

### Development Investigation Requirements
Claude Code should use the available MCP tools (including Playwright) during the development cycle to:
1. **Understand Page Structure**: Analyze DOM elements, CSS selectors, and page layouts
2. **Identify Patterns**: Recognize how availability is indicated (circles, colors, text, etc.)
3. **Extract Data**: Programmatically determine the best selectors and parsing logic
4. **Handle Variations**: Account for different calendar layouts or date formats encountered

## Configuration Example

```json
{
  "target_dates": ["2024-11-04", "2024-11-05", "2024-11-06"],
  "notification_endpoint": "https://notification.baileys.dev"
}
```

## Notification Payload Example

```json
{
  "accommodation_name": "Gassho House Yamakyu",
  "available_dates": ["2024-11-04", "2024-11-05"],
  "link": "https://www6.489pro.com/asp/489/date.asp?id=21560022&room=3&plan=145",
  "location": "Ogimachi, Shirakawa-go",
  "discovered_at": "2024-10-15T14:30:00Z"
}
```

## Error Handling Strategy
- **Network Errors**: Retry with exponential backoff (max 3 attempts)
- **Parsing Errors**: Log detailed error info and continue processing
- **Site Changes**: Graceful degradation with detailed logging for debugging
- **Configuration Errors**: Fail fast on startup with clear error messages

## Logging Strategy
- **Structured Logging**: JSON format for easy parsing
- **Log Levels**:
  - `DEBUG`: Detailed scraping steps and browser interactions
  - `INFO`: Successful checks, availability found/not found
  - `WARNING`: Recoverable errors, site structure changes
  - `ERROR`: Failed checks, notification failures

## Container Specifications

### Dockerfile Requirements
- **Base Image**: Official Python/Go image with required web scraping dependencies
- **Multi-stage Build**: Separate build and runtime stages for smaller final image
- **Non-root User**: Run container as non-privileged user
- **Health Check**: Include HEALTHCHECK instruction
- **Browser Dependencies**: Install required system packages for web automation

### Runtime Configuration
- **Environment Variables**:
  - `CONFIG_PATH`: Path to config.json (default: `/app/config.json`)
  - `LOG_LEVEL`: Override logging level
  - `NOTIFICATION_ENDPOINT`: Override notification URL
- **Volumes**: Mount point for configuration file
- **Network**: Outbound HTTPS access required

## Testing Strategy

### Verification Requirements
**Claude Code must test and verify the solution by**:
- **Visual Inspection**: Navigate to the actual websites and capture screenshots for comparison
- **Data Validation**: Compare the availability information extracted by the service against what's visually displayed on the calendar pages
- **Manual Verification**: Cross-reference service output with manually observed availability on the actual booking sites
- **End-to-End Testing**: Run the complete workflow and verify notifications are sent correctly when availability is detected

### Documentation Requirements
**Claude Code must create a technical investigation document** that includes:
- **Decision Rationale**: Explain the reasoning behind key implementation choices
- **Site Analysis Findings**: Document observations from investigating the booking sites using MCP tools
- **Parsing Strategy**: Detail how availability indicators are detected and interpreted
- **Testing Results**: Record verification steps and their outcomes
- **Technical Challenges**: Document any obstacles encountered and how they were resolved
- **Architecture Decisions**: Justify the chosen approach and structure

### Mock Services
- **Notification Service**: Docker container with HTTP endpoint for testing
- **Sample HTML**: Static HTML files mimicking real booking sites for development testing

### Test Scenarios
- **Happy Path**: Available dates found and notification sent
- **No Availability**: Complete check cycle with no matches
- **Site Unavailable**: Handle network timeouts and 500 errors
- **Invalid Config**: Proper validation error messages
- **Notification Failure**: Retry logic verification

## Development Guidelines

### Code Organization
```
/
├── src/
│   ├── config/
│   │   ├── schema.py/go
│   │   └── loader.py/go
│   ├── scrapers/
│   │   ├── base.py/go
│   │   └── shirakawa_scraper.py/go
│   ├── notifications/
│   │   └── client.py/go
│   └── main.py/go
├── tests/
├── docker/
├── config.example.json
├── Dockerfile
└── README.md
```

### Error Messages
- **User-Friendly**: Clear explanations for configuration errors
- **Developer-Friendly**: Detailed technical info in logs
- **Actionable**: Include suggestions for fixing issues

## Non-Functional Requirements

### Performance
- **Response Time**: Complete check cycle within 5 minutes per site
- **Resource Usage**: < 512MB RAM, minimal CPU when idle
- **Concurrent Checks**: Support checking multiple sites simultaneously

### Reliability
- **Uptime**: Handle 24/7 operation via cron scheduling
- **Data Consistency**: Prevent duplicate notifications for same availability
- **Recovery**: Automatic recovery from transient failures

### Maintainability
- **Extensible Design**: Easy to add new booking sites
- **Configuration Changes**: No code changes required for new monitoring targets
- **Debugging**: Comprehensive logging for troubleshooting site changes

## Out of Scope

The following items are explicitly out of scope for this implementation:

- **Cron Scheduling System**: External scheduling mechanism
- **Notification Service Implementation**: Only client-side HTTP POST integration
- **User Interface**: No web UI or dashboard
- **Data Persistence**: No database or long-term storage requirements
- **Authentication**: No user management or login systems
- **Payment Integration**: No booking automation beyond availability detection

## Example Usage

```bash
# Build container
docker build -t accommodation-checker .

# Run with custom config
docker run -v /path/to/config.json:/app/config.json accommodation-checker

# Run with environment overrides
docker run -e LOG_LEVEL=DEBUG -e NOTIFICATION_ENDPOINT=http://localhost:8080/notify accommodation-checker
```

## Success Criteria

The service will be considered successful when it can:
1. **Reliably Monitor**: Check accommodation sites without manual intervention
2. **Accurately Detect**: Identify available dates with < 5% false positives
3. **Timely Notify**: Send notifications within 1 minute of detection
4. **Operate Continuously**: Run for weeks without intervention via cron scheduling
5. **Handle Changes**: Gracefully degrade when sites change structure rather than crashing