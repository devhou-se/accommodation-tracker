#!/usr/bin/env python3
"""
Quick test for the dockerized environment.
"""
import asyncio
import sys
import os

sys.path.insert(0, '/app/src')

from config import load_config
from scrapers import ShirakawaScraper
from notifications import NotificationClient
from scrapers.base import AccommodationResult


async def quick_docker_test():
    """Quick test of the dockerized service."""
    print("🐳 Quick Docker Test Starting...")
    
    try:
        # Load configuration
        config = load_config('/app/config.json')
        print(f"✅ Config loaded: {len(config.target_dates)} target dates")
        print(f"📡 Notification endpoint: {config.notification_endpoint}")
        
        # Test notification client
        notification_client = NotificationClient(
            endpoint_url=str(config.notification_endpoint),
            timeout_seconds=config.timeout_seconds,
            retry_attempts=config.retry_attempts
        )
        
        print("🧪 Testing notification endpoint...")
        endpoint_works = await notification_client.test_endpoint()
        if endpoint_works:
            print("✅ Notification endpoint working")
        else:
            print("❌ Notification endpoint failed")
            return False
        
        # Create a simple test notification
        test_result = AccommodationResult(
            accommodation_name="Docker Test Accommodation",
            available_dates=config.target_dates[:2],  # First 2 target dates
            link="https://example.com/docker-test",
            location="Docker Test Location"
        )
        
        print("📤 Sending test notification...")
        success = await notification_client.send_notification(test_result)
        
        if success:
            print("✅ Test notification sent successfully!")
            print("🎉 DOCKER TEST PASSED!")
            return True
        else:
            print("❌ Failed to send test notification")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_docker_test())
    sys.exit(0 if success else 1)