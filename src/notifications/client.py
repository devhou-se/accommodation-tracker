import asyncio
import json
from typing import List, Optional
from datetime import datetime
import aiohttp
import structlog

try:
    from ..scrapers.base import AccommodationResult
except ImportError:
    from scrapers.base import AccommodationResult

logger = structlog.get_logger()


class NotificationClient:
    """HTTP client for sending availability notifications."""
    
    def __init__(self, endpoint_url: str, timeout_seconds: int = 30, retry_attempts: int = 3):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.logger = logger.bind(component="notification_client")
    
    async def send_notification(self, result: AccommodationResult) -> bool:
        """
        Send a notification for an accommodation availability result.
        
        Args:
            result: AccommodationResult with availability information
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        payload = self._build_payload(result)
        
        for attempt in range(self.retry_attempts):
            try:
                success = await self._send_http_notification(payload)
                if success:
                    self.logger.info(
                        "Notification sent successfully",
                        accommodation=result.accommodation_name,
                        dates=result.available_dates,
                        attempt=attempt + 1
                    )
                    return True
                else:
                    self.logger.warning(
                        "Notification failed",
                        accommodation=result.accommodation_name,
                        attempt=attempt + 1,
                        max_attempts=self.retry_attempts
                    )
            except Exception as e:
                self.logger.error(
                    "Notification error",
                    accommodation=result.accommodation_name,
                    attempt=attempt + 1,
                    error=str(e)
                )
            
            if attempt < self.retry_attempts - 1:
                # Exponential backoff: 2^attempt seconds
                wait_time = 2 ** attempt
                self.logger.info(f"Retrying in {wait_time} seconds", wait_time=wait_time)
                await asyncio.sleep(wait_time)
        
        self.logger.error(
            "All notification attempts failed",
            accommodation=result.accommodation_name,
            max_attempts=self.retry_attempts
        )
        return False
    
    async def send_notifications(self, results: List[AccommodationResult]) -> int:
        """
        Send notifications for multiple results.
        
        Args:
            results: List of AccommodationResult objects
            
        Returns:
            int: Number of notifications sent successfully
        """
        if not results:
            self.logger.info("No results to notify")
            return 0
        
        tasks = [self.send_notification(result) for result in results]
        success_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_count = sum(1 for result in success_results if result is True)
        
        self.logger.info(
            "Notification batch completed",
            total_results=len(results),
            successful=successful_count,
            failed=len(results) - successful_count
        )
        
        return successful_count
    
    def _build_payload(self, result: AccommodationResult) -> dict:
        """Build notification payload matching the expected format."""
        return {
            "accommodation_name": result.accommodation_name,
            "available_dates": result.available_dates,
            "link": result.link,
            "location": result.location,
            "discovered_at": result.discovered_at,
            "price_info": result.price_info
        }
    
    async def _send_http_notification(self, payload: dict) -> bool:
        """Send HTTP POST notification to the configured endpoint."""
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.endpoint_url,
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'Ryokan-Checker/1.0'
                    }
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        response_text = await response.text()
                        self.logger.warning(
                            "Notification endpoint returned error",
                            status_code=response.status,
                            response=response_text[:500]  # Limit log size
                        )
                        return False
                        
        except aiohttp.ClientError as e:
            self.logger.error("HTTP client error", error=str(e))
            raise
        except asyncio.TimeoutError:
            self.logger.error("Notification request timed out")
            raise
        except Exception as e:
            self.logger.error("Unexpected notification error", error=str(e))
            raise
    
    async def test_endpoint(self) -> bool:
        """Test the notification endpoint with a dummy payload."""
        test_payload = {
            "accommodation_name": "Test Hotel",
            "available_dates": ["2024-12-25"],
            "link": "https://example.com/test",
            "location": "Test Location",
            "discovered_at": datetime.utcnow().isoformat() + "Z",
            "price_info": None,
            "_test": True  # Flag to indicate this is a test
        }
        
        try:
            success = await self._send_http_notification(test_payload)
            if success:
                self.logger.info("Endpoint test successful")
            else:
                self.logger.warning("Endpoint test failed")
            return success
        except Exception as e:
            self.logger.error("Endpoint test error", error=str(e))
            return False