#!/usr/bin/env python3
"""
Test the accommodation checker service with a dockerized mock notification service.
This simulates the full dockerized environment without building the main service image.
"""
import asyncio
import sys
import os
import subprocess
import time
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers import ShirakawaScraper
from notifications import NotificationClient
from config import load_config


async def test_with_external_mock():
    """Test the service with external dockerized mock notification service."""
    print("🚀 Starting Dockerized Mock Notification Service Test")
    print("=" * 60)
    
    # Start mock notification service
    print("📦 Starting mock notification container...")
    mock_container = subprocess.run([
        'docker', 'run', '--rm', '-d', 
        '-p', '8081:3000', 
        '--name', 'test-notification-mock',
        'mock-notification'
    ], capture_output=True, text=True)
    
    if mock_container.returncode != 0:
        print(f"❌ Failed to start mock container: {mock_container.stderr}")
        return False
    
    container_id = mock_container.stdout.strip()
    print(f"✅ Mock container started: {container_id[:12]}...")
    
    # Wait for service to be ready
    print("⏳ Waiting for mock service to be ready...")
    for i in range(10):
        try:
            response = requests.get('http://localhost:8081/health', timeout=5)
            if response.status_code == 200:
                print("✅ Mock notification service is ready")
                break
        except:
            time.sleep(1)
    else:
        print("❌ Mock service failed to start")
        subprocess.run(['docker', 'stop', 'test-notification-mock'])
        return False
    
    try:
        # Test notification client
        print("\n📨 Testing notification client...")
        notification_client = NotificationClient(
            endpoint_url="http://localhost:8081/notify",
            timeout_seconds=30,
            retry_attempts=3
        )
        
        # Test notification endpoint
        endpoint_works = await notification_client.test_endpoint()
        if endpoint_works:
            print("✅ Notification endpoint test successful")
        else:
            print("❌ Notification endpoint test failed")
            return False
        
        # Test with single accommodation (quick test)
        print("\n🏠 Testing accommodation scraper with single accommodation...")
        scraper = ShirakawaScraper(timeout_seconds=30)
        
        target_dates = ["2025-08-27", "2025-08-28", "2025-08-31"]
        
        try:
            await scraper._initialize_browser()
            
            # Test just Rihee (which we know has availability)
            acc_info = {
                'name': 'Rihee', 
                'url': 'https://shirakawa-go.gr.jp/en/stay/33/'
            }
            
            print(f"🔍 Checking {acc_info['name']} for dates: {target_dates}")
            result = await scraper._check_single_accommodation(acc_info, target_dates)
            
            if result:
                print(f"✅ Found availability: {result.available_dates}")
                
                # Send notification
                print("📤 Sending notification...")
                success = await notification_client.send_notification(result)
                
                if success:
                    print("✅ Notification sent successfully!")
                    
                    # Check mock service received it
                    print("🔍 Checking notifications received...")
                    response = requests.get('http://localhost:8081/notifications')
                    data = response.json()
                    
                    print(f"📊 Mock service received {data['count']} notifications")
                    if data['count'] > 0:
                        latest = data['notifications'][-1]
                        print(f"📋 Latest notification: {latest['accommodation_name']} - {latest['available_dates']}")
                        print("🎉 END-TO-END TEST PASSED!")
                        return True
                    else:
                        print("❌ No notifications received by mock service")
                        return False
                else:
                    print("❌ Failed to send notification")
                    return False
            else:
                print("⚠️  No availability found (this may be normal)")
                # Still test notification with dummy data
                from scrapers.base import AccommodationResult
                dummy_result = AccommodationResult(
                    accommodation_name="Test Accommodation",
                    available_dates=["2025-12-25"],
                    link="https://example.com/test",
                    location="Test Location"
                )
                
                print("📤 Sending test notification...")
                success = await notification_client.send_notification(dummy_result)
                if success:
                    print("✅ Test notification sent successfully!")
                    return True
                else:
                    print("❌ Failed to send test notification")
                    return False
                    
        finally:
            await scraper.cleanup()
            
    except Exception as e:
        print(f"💥 Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        print("📋 Mock service logs:")
        subprocess.run(['docker', 'logs', 'test-notification-mock'])
        subprocess.run(['docker', 'stop', 'test-notification-mock'])
        print("✅ Cleanup complete")


if __name__ == "__main__":
    success = asyncio.run(test_with_external_mock())
    if success:
        print("\n🎉 DOCKERIZED MOCK TEST PASSED!")
        sys.exit(0)
    else:
        print("\n❌ DOCKERIZED MOCK TEST FAILED!")
        sys.exit(1)