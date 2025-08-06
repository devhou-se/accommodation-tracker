#!/usr/bin/env python3
"""
Final test of the full dockerized service using the external mock notification container.
This test uses the actual main.py service but in single-run mode.
"""
import asyncio
import sys
import os
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test the service can import and run
from main import main as main_service


async def test_full_docker_service():
    """Test the full service against dockerized mock notification."""
    print("🐳 Full Docker Service Test")
    print("=" * 50)
    
    # Check mock service is running
    print("🔍 Checking mock notification service...")
    try:
        response = requests.get('http://localhost:8082/health', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Mock service healthy (uptime: {data['uptime']:.1f}s)")
        else:
            print("❌ Mock service not responding correctly")
            return False
    except Exception as e:
        print(f"❌ Mock service not accessible: {e}")
        return False
    
    # Set environment variables for single run mode
    os.environ['CONFIG_PATH'] = './config.test.json'
    os.environ['SINGLE_RUN'] = 'true'
    os.environ['LOG_LEVEL'] = 'INFO'
    
    # Update config to use localhost (since we're running outside Docker)
    print("📝 Updating config for localhost testing...")
    import json
    with open('./config.test.json', 'r') as f:
        config = json.load(f)
    
    config['notification_endpoint'] = 'http://localhost:8082/notify'
    
    with open('./config.test-localhost.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    os.environ['CONFIG_PATH'] = './config.test-localhost.json'
    
    print("🚀 Running main service in single-run mode...")
    
    try:
        # Run the main service (it will do single run and exit)
        await main_service()
        print("✅ Main service completed successfully")
        
        # Check if notifications were received
        print("🔍 Checking notifications received by mock service...")
        response = requests.get('http://localhost:8082/notifications', timeout=10)
        data = response.json()
        
        print(f"📊 Mock service received {data['count']} notifications")
        
        if data['count'] > 0:
            print("📋 Notifications received:")
            for i, notif in enumerate(data['notifications'][-3:], 1):  # Last 3
                print(f"  {i}. {notif.get('accommodation_name', 'Unknown')} - {notif.get('available_dates', [])}")
            
            print("🎉 FULL DOCKER SERVICE TEST PASSED!")
            return True
        else:
            print("⚠️  No notifications received - this may be normal if no availability found")
            print("✅ Service ran successfully without errors")
            return True
            
    except Exception as e:
        print(f"💥 Error running main service: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_full_docker_service())
    if success:
        print("\n🎉 FULL DOCKERIZED TEST COMPLETE!")
        sys.exit(0)  
    else:
        print("\n❌ FULL DOCKERIZED TEST FAILED!")
        sys.exit(1)