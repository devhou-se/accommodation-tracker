# Testing Guide

Comprehensive testing guide for the Japanese Accommodation Availability Checker.

## Test Categories

### 1. Unit Tests
- Configuration validation
- Scraper logic
- Notification client
- Utility functions

### 2. Integration Tests  
- Browser automation
- External API calls
- Docker container health

### 3. End-to-End Tests
- Full scraping workflow
- Notification delivery
- Error handling scenarios

### 4. Performance Tests
- Memory usage validation
- Response time measurements
- Concurrent operation testing

## Quick Testing

### Mock Service Test

Test with external mock notification service:

```bash
# Start mock notification container
docker compose -f docker-compose.final-test.yml up -d

# Run full service test
python test_full_docker.py

# Check notifications received
curl http://localhost:8082/notifications
```

### Single Component Tests

```bash
# Test configuration loading
python -c "from config import load_config; print(load_config('./config.json'))"

# Test scraper only
python quick_test.py

# Test notification client
python test_with_mock.py
```

## Detailed Test Procedures

### Configuration Testing

#### Valid Configuration Test
```python
#!/usr/bin/env python3
import json
from src.config import load_config

def test_valid_config():
    """Test loading a valid configuration."""
    config_data = {
        "target_dates": ["2025-08-27", "2025-08-28"],
        "notification_endpoint": "https://example.com/webhook",
        "log_level": "INFO"
    }
    
    with open('test-config.json', 'w') as f:
        json.dump(config_data, f)
    
    config = load_config('test-config.json')
    assert len(config.target_dates) == 2
    assert config.log_level == "INFO"
    print("✅ Valid configuration test passed")

if __name__ == "__main__":
    test_valid_config()
```

#### Invalid Configuration Test
```python
def test_invalid_date_format():
    """Test configuration with invalid date format."""
    config_data = {
        "target_dates": ["27/08/2025"],  # Invalid format
        "notification_endpoint": "https://example.com/webhook"
    }
    
    with open('test-invalid-config.json', 'w') as f:
        json.dump(config_data, f)
    
    try:
        config = load_config('test-invalid-config.json')
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "Invalid date format" in str(e)
        print("✅ Invalid date format test passed")
```

### Scraper Testing

#### Website Accessibility Test
```python
#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper

async def test_website_accessibility():
    """Test that target websites are accessible."""
    scraper = ShirakawaScraper(timeout_seconds=30)
    
    try:
        await scraper._initialize_browser()
        page = await scraper.context.new_page()
        
        # Test main search page
        response = await page.goto(scraper.SEARCH_URL)
        assert response.status == 200, f"Search page returned {response.status}"
        print("✅ Search page accessible")
        
        # Test individual accommodation page  
        await page.goto("https://shirakawa-go.gr.jp/en/stay/33/")
        print("✅ Individual accommodation page accessible")
        
        await page.close()
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(test_website_accessibility())
```

#### Accommodation List Extraction Test
```python
async def test_accommodation_extraction():
    """Test accommodation list extraction."""
    scraper = ShirakawaScraper()
    
    try:
        accommodations = await scraper._get_accommodation_list()
        
        assert len(accommodations) > 0, "No accommodations found"
        assert len(accommodations) <= 15, "Too many accommodations found"
        
        for acc in accommodations:
            assert 'name' in acc, "Accommodation missing name"
            assert 'url' in acc, "Accommodation missing URL"
            assert acc['url'].startswith('https://'), "Invalid URL format"
        
        print(f"✅ Found {len(accommodations)} accommodations")
    finally:
        await scraper.cleanup()
```

### Notification Client Testing

#### HTTP Endpoint Test
```python
#!/usr/bin/env python3
import asyncio
import aiohttp
from aiohttp import web
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from notifications import NotificationClient
from scrapers.base import AccommodationResult

async def create_test_server():
    """Create a test HTTP server for notifications."""
    received_notifications = []
    
    async def handle_notification(request):
        data = await request.json()
        received_notifications.append(data)
        return web.json_response({"status": "success"})
    
    app = web.Application()
    app.router.add_post('/notify', handle_notification)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8083)
    await site.start()
    
    return runner, received_notifications

async def test_notification_client():
    """Test notification client functionality."""
    runner, notifications = await create_test_server()
    
    try:
        client = NotificationClient("http://localhost:8083/notify")
        
        # Test endpoint
        assert await client.test_endpoint(), "Endpoint test failed"
        
        # Test notification
        result = AccommodationResult(
            accommodation_name="Test Hotel",
            available_dates=["2025-12-25"],
            link="https://example.com",
            location="Test Location"
        )
        
        success = await client.send_notification(result)
        assert success, "Notification sending failed"
        assert len(notifications) == 2, f"Expected 2 notifications, got {len(notifications)}"
        
        print("✅ Notification client test passed")
        
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(test_notification_client())
```

### Docker Testing

#### Container Build Test
```bash
#!/bin/bash
# test_docker_build.sh

echo "🐳 Testing Docker build..."

# Build the image
docker build -t accommodation-checker-test . || exit 1
echo "✅ Docker build successful"

# Test container can start
docker run --rm --name test-container -d \
  -e SINGLE_RUN=true \
  -e CONFIG_PATH=/app/config.example.json \
  accommodation-checker-test || exit 1

sleep 5

# Check container is running
if docker ps | grep -q test-container; then
    echo "✅ Container started successfully"
    docker stop test-container
else
    echo "❌ Container failed to start"
    exit 1
fi

echo "🎉 Docker tests passed"
```

#### Container Health Test
```bash
#!/bin/bash
# test_container_health.sh

echo "🏥 Testing container health..."

# Start container with health checks
docker compose -f docker-compose.test.yml up -d

# Wait for health check
for i in {1..30}; do
    if docker compose -f docker-compose.test.yml ps | grep -q "healthy"; then
        echo "✅ Container is healthy"
        docker compose -f docker-compose.test.yml down
        exit 0
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 2
done

echo "❌ Container health check failed"
docker compose -f docker-compose.test.yml logs
docker compose -f docker-compose.test.yml down
exit 1
```

## Automated Test Suite

### Test Runner Script
```python
#!/usr/bin/env python3
"""
Automated test suite runner for the accommodation checker.
"""
import asyncio
import subprocess
import sys
import os
import tempfile
import json

class TestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def run_test(self, test_name, test_func):
        """Run a single test and record results."""
        try:
            print(f"Running {test_name}...")
            result = test_func()
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            
            self.passed += 1
            self.results.append(f"✅ {test_name}: PASSED")
            print(f"✅ {test_name}: PASSED")
            
        except Exception as e:
            self.failed += 1
            self.results.append(f"❌ {test_name}: FAILED - {str(e)}")
            print(f"❌ {test_name}: FAILED - {str(e)}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        for result in self.results:
            print(result)
        
        print(f"\nTotal: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n❌ {self.failed} TESTS FAILED")
            return 1

def test_config_validation():
    """Test configuration validation."""
    sys.path.insert(0, 'src')
    from config import load_config
    
    # Valid config
    valid_config = {
        "target_dates": ["2025-08-27"],
        "notification_endpoint": "https://example.com/webhook"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(valid_config, f)
        temp_file = f.name
    
    try:
        config = load_config(temp_file)
        assert len(config.target_dates) == 1
    finally:
        os.unlink(temp_file)

def test_docker_build():
    """Test Docker image can be built."""
    result = subprocess.run(['docker', 'build', '-t', 'test-accommodation-checker', '.'], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Docker build failed: {result.stderr}")

async def test_scraper_initialization():
    """Test scraper can be initialized."""
    sys.path.insert(0, 'src')
    from scrapers import ShirakawaScraper
    
    scraper = ShirakawaScraper()
    await scraper._initialize_browser()
    await scraper.cleanup()

def main():
    """Run all tests."""
    suite = TestSuite()
    
    # Configuration tests
    suite.run_test("Config Validation", test_config_validation)
    
    # Docker tests
    suite.run_test("Docker Build", test_docker_build)
    
    # Scraper tests
    suite.run_test("Scraper Initialization", test_scraper_initialization)
    
    return suite.print_summary()

if __name__ == "__main__":
    sys.exit(main())
```

## Performance Testing

### Memory Usage Test
```python
#!/usr/bin/env python3
import asyncio
import psutil
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper

async def test_memory_usage():
    """Test memory usage doesn't exceed limits."""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    scraper = ShirakawaScraper()
    
    try:
        await scraper._initialize_browser()
        
        # Simulate checking accommodations
        for i in range(3):
            accommodations = await scraper._get_accommodation_list()
            current_memory = process.memory_info().rss / 1024 / 1024
            
            print(f"Iteration {i+1}: {current_memory:.1f}MB")
            
            # Check memory doesn't exceed 500MB
            assert current_memory < 500, f"Memory usage too high: {current_memory}MB"
    
    finally:
        await scraper.cleanup()
        
    final_memory = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB")
    print("✅ Memory usage test passed")

if __name__ == "__main__":
    asyncio.run(test_memory_usage())
```

### Response Time Test
```python
#!/usr/bin/env python3
import asyncio
import time
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper

async def test_response_times():
    """Test response times are within acceptable limits."""
    scraper = ShirakawaScraper(timeout_seconds=30)
    
    try:
        # Test accommodation list extraction
        start_time = time.time()
        accommodations = await scraper._get_accommodation_list()
        list_time = time.time() - start_time
        
        assert list_time < 15, f"Accommodation list took too long: {list_time:.1f}s"
        print(f"✅ Accommodation list: {list_time:.1f}s")
        
        # Test single accommodation check
        if accommodations:
            acc = accommodations[0]
            start_time = time.time()
            result = await scraper._check_single_accommodation(acc, ["2025-12-25"])
            single_time = time.time() - start_time
            
            assert single_time < 60, f"Single check took too long: {single_time:.1f}s"
            print(f"✅ Single accommodation: {single_time:.1f}s")
    
    finally:
        await scraper.cleanup()

if __name__ == "__main__":
    asyncio.run(test_response_times())
```

## Test Data & Fixtures

### Mock Configuration
```json
{
  "target_dates": ["2025-12-25", "2025-12-26"],
  "notification_endpoint": "http://localhost:8083/webhook",
  "log_level": "DEBUG",
  "check_interval_seconds": 60,
  "retry_attempts": 2,
  "timeout_seconds": 15
}
```

### Test Notifications
```python
# Expected notification payloads for testing
TEST_NOTIFICATIONS = [
    {
        "accommodation_name": "Test Hotel 1",
        "available_dates": ["2025-12-25"],
        "link": "https://example.com/hotel1",
        "location": "Test Location 1",
        "discovered_at": "2025-08-06T12:00:00Z"
    },
    {
        "accommodation_name": "Test Hotel 2", 
        "available_dates": ["2025-12-25", "2025-12-26"],
        "link": "https://example.com/hotel2",
        "location": "Test Location 2",
        "discovered_at": "2025-08-06T12:01:00Z"
    }
]
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        playwright install chromium
    
    - name: Run tests
      run: |
        python test_suite.py
    
    - name: Test Docker build
      run: |
        docker build -t test-image .
    
    - name: Run integration tests
      run: |
        docker compose -f docker-compose.test.yml up -d
        python test_full_docker.py
        docker compose -f docker-compose.test.yml down
```

## Test Maintenance

### Regular Test Updates
- Update target dates to future dates monthly
- Verify external endpoints are still accessible
- Check for site structure changes quarterly
- Update browser versions when Playwright releases updates

### Test Environment Cleanup
```bash
#!/bin/bash
# cleanup_test_env.sh

# Stop all test containers
docker stop $(docker ps -q --filter "name=*test*") 2>/dev/null || true

# Remove test containers
docker rm $(docker ps -aq --filter "name=*test*") 2>/dev/null || true

# Remove test images
docker rmi $(docker images -q "*test*") 2>/dev/null || true

# Clean up test files
rm -f config.test-*.json
rm -f test-*.json

echo "✅ Test environment cleaned up"
```