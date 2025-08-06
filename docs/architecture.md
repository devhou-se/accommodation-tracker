# Architecture Overview

Detailed overview of the Japanese Accommodation Availability Checker architecture, design decisions, and system components.

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Config File   │    │  Main Service   │    │  Notification   │
│   (JSON)        │────▶│  (Python)       │────▶│  Endpoint       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Web Scraper    │
                       │  (Playwright)   │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Target Sites   │
                       │  (shirakawa-go) │
                       └─────────────────┘
```

## Core Components

### 1. Configuration Manager (`src/config/`)

**Purpose**: Manages application configuration with validation

**Components**:
- `schema.py`: Pydantic models for configuration validation
- `loader.py`: Configuration loading with environment overrides

**Key Features**:
- JSON schema validation
- Environment variable overrides
- Type safety with Pydantic
- Fail-fast validation

```python
class Config(BaseModel):
    target_dates: List[str]
    notification_endpoint: HttpUrl
    log_level: str = "INFO"
    # ... additional fields
```

### 2. Web Scraper (`src/scrapers/`)

**Purpose**: Automated web scraping of accommodation booking sites

**Components**:
- `base.py`: Abstract base class for all scrapers
- `shirakawa_scraper.py`: Shirakawa-go specific implementation

**Architecture Pattern**: Strategy Pattern
- Base class defines interface
- Concrete implementations for different sites
- Easy to extend for new booking sites

```python
class BaseScraper(ABC):
    @abstractmethod
    async def check_availability(self, target_dates: List[str]) -> List[AccommodationResult]:
        pass
```

### 3. Notification Client (`src/notifications/`)

**Purpose**: HTTP client for sending availability notifications

**Features**:
- Exponential backoff retry logic
- Structured payload formatting
- Error handling and logging
- Connection pooling with aiohttp

```python
class NotificationClient:
    async def send_notification(self, result: AccommodationResult) -> bool:
        # Retry logic with exponential backoff
```

### 4. Main Application (`src/main.py`)

**Purpose**: Orchestrates the entire application lifecycle

**Responsibilities**:
- Service initialization and coordination
- Main event loop management
- Signal handling for graceful shutdown
- Health check endpoint
- Structured logging setup

## Design Patterns

### 1. Strategy Pattern (Scrapers)
- Different scraping strategies for different sites
- Easy to add new booking sites
- Consistent interface across implementations

### 2. Observer Pattern (Notifications)
- Decoupled notification sending
- Multiple notification channels possible
- Event-driven architecture

### 3. Factory Pattern (Browser Management)
- Centralized browser instance creation
- Resource lifecycle management
- Consistent browser configuration

### 4. Circuit Breaker (Error Handling)
- Prevents cascade failures
- Graceful degradation
- Automatic recovery

## Data Flow

### 1. Initialization
```
Config Loading → Validation → Component Initialization → Health Checks
```

### 2. Main Loop
```
Schedule Check → Initialize Browser → Scrape Sites → Process Results → Send Notifications → Wait → Repeat
```

### 3. Scraping Process
```
Load Site List → Visit Each Site → Extract Availability → Filter Target Dates → Return Results
```

### 4. Notification Process
```
Format Payload → HTTP POST → Retry on Failure → Log Result
```

## Technology Stack

### Core Technologies
- **Python 3.11+**: Main runtime and application logic
- **Playwright**: Browser automation for web scraping
- **aiohttp**: Async HTTP client for notifications
- **Pydantic**: Data validation and settings management
- **structlog**: Structured logging

### Infrastructure
- **Docker**: Containerization and deployment
- **Docker Compose**: Multi-container orchestration
- **Alpine Linux**: Minimal container base images

## Concurrency Model

### Async/Await Architecture
```python
async def main_loop():
    while running:
        await check_availability()  # Async scraping
        await send_notifications()  # Async HTTP requests
        await asyncio.sleep(interval)
```

### Benefits:
- Non-blocking I/O operations
- Efficient resource utilization
- Scalable under load
- Proper async context management

## Error Handling Strategy

### Multi-Level Error Handling

1. **Component Level**: Each component handles its own errors
2. **Service Level**: Main service catches and logs unhandled errors
3. **Infrastructure Level**: Docker health checks and restart policies

### Error Types

```python
# Configuration Errors
class ConfigurationError(Exception): pass

# Scraping Errors  
class ScrapingError(Exception): pass

# Notification Errors
class NotificationError(Exception): pass
```

### Recovery Mechanisms
- Exponential backoff for transient failures
- Continue processing other sites if one fails
- Graceful degradation with detailed logging
- Automatic retry with circuit breaker pattern

## Security Architecture

### Container Security
- Non-root user execution
- Minimal attack surface (Alpine base)
- Read-only filesystem where possible
- Resource limits and quotas

### Network Security
- Internal Docker networks
- No unnecessary port exposure
- HTTPS for external communications
- Input validation at all boundaries

### Data Security
- No sensitive data persistence
- Secure configuration handling
- Audit logging for all actions

## Monitoring & Observability

### Structured Logging
```json
{
  "timestamp": "2025-08-06T12:47:38Z",
  "level": "info",
  "logger": "main",
  "event": "availability_found",
  "accommodation": "Rihee",
  "dates": ["2025-08-27", "2025-08-28"]
}
```

### Health Checks
- Container health check endpoint
- Application-level health verification
- External dependency health monitoring

### Metrics
- Request latency and success rates
- Availability detection rates
- Resource utilization monitoring

## Scalability Considerations

### Horizontal Scaling
- Stateless service design
- Multiple instance deployment
- Load balancing support

### Vertical Scaling
- Configurable resource limits
- Efficient memory usage
- CPU optimization

### Performance Optimization
- Browser instance reuse
- Connection pooling
- Asynchronous operations
- Minimal memory footprint

## Extension Points

### Adding New Booking Sites
1. Create new scraper class extending `BaseScraper`
2. Implement site-specific parsing logic
3. Register in main service configuration
4. No changes to other components required

### Adding Notification Channels
1. Extend `NotificationClient` or create new client
2. Implement channel-specific formatting
3. Configure in main service
4. Parallel notification support

### Adding Monitoring
1. Implement metrics collection interfaces
2. Add structured logging events
3. Export metrics in standard formats
4. Integration with monitoring systems

## Deployment Architecture

### Single Container Deployment
```
┌─────────────────────────────────┐
│         Docker Container        │
│  ┌─────────────────────────────┐│
│  │     Main Application        ││
│  │  ┌─────────┐ ┌─────────────┐││
│  │  │Scraper  │ │Notification │││
│  │  └─────────┘ └─────────────┘││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

### Multi-Container Deployment
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Main Service    │  │ Mock Notification│  │ Monitoring      │
│ Container       │──│ Container        │  │ Container       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Future Architecture Considerations

### Microservices Migration
- Split scrapers into separate services
- API gateway for coordination  
- Event-driven communication
- Independent scaling of components

### Data Persistence
- Historical availability tracking
- Trend analysis capabilities
- Database integration patterns
- Caching layer implementation

### Machine Learning Integration
- Availability prediction models
- Optimal check timing
- Anomaly detection
- Pattern recognition