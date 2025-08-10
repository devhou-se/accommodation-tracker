# Status Dashboard Guide

Beautiful, real-time web interface for monitoring the Japanese Accommodation Availability Checker.

## 🌸 Overview

The status dashboard provides a comprehensive, Japanese-inspired web interface for monitoring:
- Real-time system status and health
- Availability discoveries and history
- Performance metrics and charts
- Interactive testing and controls

## 🎌 Features

### Real-Time Monitoring
- **Live System Status**: Current service state, uptime, and health metrics
- **Activity Timeline**: Recent check cycles with success/failure indicators
- **Performance Charts**: Hourly success rates and check duration trends
- **Auto-Refresh**: Updates every 30 seconds automatically

### Availability Tracking  
- **Historical Data**: SQLite database stores all check results and discoveries
- **Discovery Timeline**: When and where availability was found
- **Accommodation Status**: Current state of all tracked gassho-zukuris
- **Notification Tracking**: Whether alerts were sent successfully

### Interactive Controls
- **Test Notifications**: Send test alerts to verify webhook endpoints
- **Manual Refresh**: Force immediate data update
- **Health Checks**: Verify all system components

### Beautiful Design
- **Japanese Aesthetic**: Traditional color palette and typography
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Real-Time Updates**: No page refreshes needed
- **Interactive Charts**: Hover for detailed metrics

## 🏯 Getting Started

### Quick Start with Dashboard

1. **Use the launcher script**:
   ```bash
   python3 start-with-dashboard.py
   ```

2. **Or start manually**:
   ```bash
   # Start all services with dashboard
   docker compose -f docker-compose.with-dashboard.yml up --build -d
   
   # Open dashboard
   open http://localhost:8000
   ```

3. **Services started**:
   - 📊 **Dashboard**: http://localhost:8000
   - 🔔 **Mock Notifications**: http://localhost:8082
   - 🏯 **Main Checker**: Running in background

### Configuration

The dashboard uses the same `config.json` as the main service:

```json
{
  "target_dates": ["2025-03-15", "2025-03-16"],
  "notification_endpoint": "http://mock-notification:8082/notify",
  "log_level": "INFO",
  "check_interval_seconds": 120,
  "retry_attempts": 3,
  "timeout_seconds": 30
}
```

## 📊 Dashboard Interface

### Header Section
- **Service Status Badge**: Real-time health indicator with color coding
- **Current Time**: Live JST time display
- **System Title**: Japanese-themed branding

### Quick Stats Cards
- **Checks Today**: Number of accommodation checks performed
- **Accommodations**: Total gassho-zukuris being monitored  
- **Availabilities**: Discoveries found today
- **Uptime**: How long the service has been running

### Main Panels

#### 🎌 System Status Panel
- Current operational state
- Last check timestamp
- Target dates being monitored
- Check interval configuration  
- Overall success rate
- Interactive test buttons

#### ⏰ Recent Activity Timeline
- Chronological list of recent check cycles
- Success/failure indicators with color coding
- Duration and performance metrics
- Error messages when applicable

#### 🏘️ Tracked Accommodations
- Grid view of all monitored gassho-zukuris
- Availability status for each property
- Recent available dates found
- Last seen timestamps

#### 📊 Performance Metrics
- **Hourly Success Rate Chart**: 24-hour trend line
- **Check Duration Chart**: Processing time trends
- Interactive hover tooltips

#### 🎉 Recent Discoveries
- Latest availability findings
- Accommodation names and dates
- Direct links to booking pages
- Notification delivery status

## 🔧 API Endpoints

The dashboard exposes several API endpoints:

### Status Endpoints
```http
GET /api/status          # Current system status
GET /api/health          # Health check
GET /api/metrics         # Performance metrics
```

### Data Endpoints  
```http
GET /api/history?hours=24        # Check history
GET /api/accommodations          # Accommodation status
```

### Control Endpoints
```http
POST /api/test-notification      # Send test alert
```

## 💾 Data Storage

### SQLite Database
The dashboard uses SQLite for persistent storage:

```
/app/data/status.db
├── check_runs          # All check cycle results
├── availability_history # Availability discoveries  
└── system_metrics      # Performance data
```

### Data Retention
- **Check Runs**: All historical data retained
- **Availability History**: All discoveries retained
- **Metrics**: Aggregated performance data
- **Database Size**: Typically <50MB for months of data

## 🎨 Customization

### Themes and Styling
The dashboard uses traditional Japanese design elements:

- **Colors**: Vermillion red, forest green, golden yellow
- **Typography**: Noto Sans JP font family
- **Layout**: Tatami mat-inspired proportions
- **Animations**: Subtle zen-like transitions

### Custom CSS Variables
```css
:root {
  --primary-color: #E74C3C;      /* Vermillion red */
  --success-color: #27AE60;      /* Forest green */
  --accent-color: #F39C12;       /* Golden yellow */
  --background-color: #FAFAFA;   /* Off-white paper */
}
```

## 🔧 Technical Architecture

### Web Framework
- **FastAPI**: Modern async web framework
- **Uvicorn**: ASGI server for high performance
- **Jinja2**: Template engine for HTML rendering

### Frontend Technologies
- **Chart.js**: Interactive performance charts
- **Axios**: HTTP client for API calls
- **Vanilla JavaScript**: No framework dependencies
- **CSS Grid**: Modern responsive layouts

### Data Flow
```
Main App → Status Tracker → SQLite → Dashboard API → Frontend
```

1. **Main application** records all activity to status tracker
2. **Status tracker** stores data in SQLite database
3. **Dashboard API** serves data via REST endpoints
4. **Frontend** fetches and displays real-time updates

## 🚀 Production Deployment

### Docker Compose Production
```yaml
services:
  accommodation-checker:
    build: .
    volumes:
      - ./config.json:/app/config.json:ro
      - accommodation-data:/app/data
    
  status-dashboard:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - accommodation-data:/app/data
    command: ["python", "/app/src/web/status_server.py"]
```

### Security Considerations
- Dashboard should be behind reverse proxy in production
- Consider authentication for sensitive environments
- Use HTTPS for external access
- Limit database access permissions

### Performance Optimization
- Dashboard caches data for 30-second intervals
- Database queries use indexes for performance
- Static assets served efficiently
- Minimal JavaScript bundle size

## 📱 Mobile Experience

The dashboard is fully responsive and mobile-friendly:

- **Touch-Friendly**: Large buttons and touch targets
- **Responsive Grid**: Adapts to all screen sizes
- **Optimized Charts**: Touch-enabled interactions
- **Fast Loading**: Minimal resource requirements

## 🛠️ Troubleshooting

### Dashboard Not Loading
```bash
# Check service health
curl http://localhost:8000/api/health

# View logs
docker compose -f docker-compose.with-dashboard.yml logs status-dashboard
```

### Data Not Updating
```bash
# Check main service
docker compose -f docker-compose.with-dashboard.yml logs accommodation-checker

# Verify database permissions
ls -la /app/data/
```

### API Errors
- Ensure status tracker is properly initialized
- Check SQLite database connectivity
- Verify configuration file is accessible

## 🎉 Fun Features

### Japanese Elements
- 🏯 Traditional architecture icons
- 🌸 Cherry blossom color themes  
- 🎌 Japanese typography
- ⛩️ Zen-inspired animations

### Easter Eggs
- Time displays in JST (Japan Standard Time)
- Success animations with Japanese flair
- Traditional spacing ratios throughout
- Seasonal color variations

The status dashboard turns monitoring into a delightful experience while providing all the technical depth you need for production operations!