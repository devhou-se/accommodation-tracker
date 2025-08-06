# Japanese Accommodation Availability Checker - Documentation

Welcome to the documentation for the Japanese Accommodation Availability Checker. This service automates monitoring of traditional Japanese accommodations (Gassho houses) in Shirakawa-go and sends notifications when target dates become available.

## 📚 Documentation Index

### Getting Started
- [Quick Start Guide](./quick-start.md) - Get up and running in minutes
- [Installation Guide](./installation.md) - Detailed installation instructions
- [Configuration Guide](./configuration.md) - How to configure the service

### Architecture & Design  
- [Architecture Overview](./architecture.md) - System design and components
- [Technical Investigation](./technical-investigation.md) - Deep dive into implementation
- [Site Analysis](./site-analysis.md) - How the scraping works

### Deployment
- [Docker Deployment](./docker-deployment.md) - Running with Docker
- [Production Deployment](./production-deployment.md) - Production-ready setup
- [Monitoring & Logging](./monitoring.md) - Operational monitoring

### Development
- [Development Setup](./development.md) - Setting up for development
- [API Reference](./api-reference.md) - Code documentation
- [Testing Guide](./testing.md) - How to test the service

### Operations
- [Troubleshooting](./troubleshooting.md) - Common issues and solutions
- [Performance Tuning](./performance.md) - Optimization guidelines
- [Security Guidelines](./security.md) - Security best practices

## 🏗️ Service Overview

The service consists of these main components:

- **Web Scraper**: Uses Playwright to automate browser interactions with Japanese booking sites
- **Configuration Manager**: JSON-based configuration with validation
- **Notification Client**: HTTP client for sending availability alerts
- **Health Monitor**: Container health checks and monitoring endpoints

## 🎯 Key Features

- ✅ **Automated Monitoring**: Continuous checking of accommodation availability
- ✅ **Smart Detection**: Identifies available dates using visual calendar indicators  
- ✅ **HTTP Notifications**: Sends JSON alerts to configured endpoints
- ✅ **Docker Ready**: Containerized for easy deployment
- ✅ **Resilient**: Handles site changes gracefully with detailed logging
- ✅ **Configurable**: JSON-based configuration with environment variable overrides

## 🚀 Quick Example

```bash
# Run with Docker
docker compose up

# Run with Python
export CONFIG_PATH=./config.json
python src/main.py
```

## 🛠️ Support

For issues, questions, or contributions:
- Check the [Troubleshooting Guide](./troubleshooting.md)
- Review the [Technical Investigation](./technical-investigation.md)
- Examine the logs for detailed error information

## 📄 License

This project is for educational and personal use. Please respect the terms of service of monitored websites.