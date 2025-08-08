import os
import json
import asyncio
from typing import List, Optional
import structlog
import aiohttp
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To

from config import Config


class NotificationClient:
    """Client for sending availability notifications via SendGrid email."""
    
    def __init__(self, endpoint_url: str, timeout_seconds: int = 30, retry_attempts: int = 3, config: Optional[Config] = None):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.config = config
        self.logger = structlog.get_logger()
        
        # Initialize SendGrid client if API key is available
        self.sendgrid_client = None
        if config and hasattr(config, 'sendgrid_api_key') and config.sendgrid_api_key:
            # Replace environment variable placeholder with actual value
            api_key = config.sendgrid_api_key
            if api_key.startswith('${') and api_key.endswith('}'):
                env_var = api_key[2:-1]  # Remove ${ and }
                api_key = os.getenv(env_var)
            
            if api_key:
                self.sendgrid_client = SendGridAPIClient(api_key=api_key)
                self.logger.info("SendGrid client initialized")
            else:
                self.logger.warning("SendGrid API key not found in environment")
    
    async def send_notifications(self, results: List) -> int:
        """Send notifications for availability results."""
        if not results:
            return 0
        
        success_count = 0
        
        # Try SendGrid email notifications first
        if self.sendgrid_client and self.config and hasattr(self.config, 'notification_emails'):
            try:
                await self._send_email_notifications(results)
                success_count += len(self.config.notification_emails)
                self.logger.info("Email notifications sent successfully", count=success_count)
            except Exception as e:
                self.logger.error("Failed to send email notifications", error=str(e))
        
        # Fallback to HTTP notification (for mock server compatibility)
        try:
            http_success = await self._send_http_notifications(results)
            if http_success:
                success_count += 1
        except Exception as e:
            self.logger.error("Failed to send HTTP notifications", error=str(e))
        
        return success_count
    
    async def _send_email_notifications(self, results: List):
        """Send email notifications via SendGrid."""
        if not self.config or not hasattr(self.config, 'notification_emails'):
            return
        
        # Build email content
        subject = f"🏯 Ryokan Availability Found - {len(results)} accommodation(s) available!"
        
        # Create HTML content
        html_content = self._build_email_html(results)
        text_content = self._build_email_text(results)
        
        # Send to all configured email addresses
        for email in self.config.notification_emails:
            try:
                message = Mail(
                    from_email=self.config.email_from,
                    to_emails=To(email),
                    subject=subject,
                    html_content=html_content,
                    plain_text_content=text_content
                )
                
                response = self.sendgrid_client.send(message)
                self.logger.info("Email sent", email=email, status_code=response.status_code)
                
            except Exception as e:
                self.logger.error("Failed to send email", email=email, error=str(e))
                raise
    
    async def _send_http_notifications(self, results: List) -> bool:
        """Send HTTP notifications (fallback/compatibility)."""
        payload = {
            "message": f"Found {len(results)} accommodation(s) with availability",
            "results": [
                {
                    "accommodation": result.accommodation_name,
                    "dates": result.available_dates,
                    "url": result.url
                }
                for result in results
            ]
        }
        
        for attempt in range(self.retry_attempts):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)) as session:
                    async with session.post(self.endpoint_url, json=payload) as response:
                        if response.status == 200:
                            self.logger.info("HTTP notification sent successfully", attempt=attempt + 1)
                            return True
                        else:
                            self.logger.warning("HTTP notification failed", status=response.status, attempt=attempt + 1)
            except Exception as e:
                self.logger.error("HTTP notification error", error=str(e), attempt=attempt + 1)
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def _build_email_html(self, results: List) -> str:
        """Build HTML email content."""
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                .header { background: linear-gradient(135deg, #8B4513 0%, #D2691E 100%); color: white; padding: 30px 20px; text-align: center; }
                .header h1 { margin: 0; font-size: 28px; }
                .header p { margin: 10px 0 0 0; opacity: 0.9; }
                .content { padding: 30px 20px; }
                .accommodation { border: 1px solid #e0e0e0; border-radius: 8px; margin: 20px 0; padding: 20px; background-color: #fafafa; }
                .accommodation h3 { margin: 0 0 10px 0; color: #8B4513; }
                .dates { margin: 10px 0; }
                .date { display: inline-block; background-color: #8B4513; color: white; padding: 4px 8px; border-radius: 4px; margin: 2px; font-size: 14px; }
                .link { margin-top: 15px; }
                .link a { color: #8B4513; text-decoration: none; font-weight: bold; }
                .footer { background-color: #f8f8f8; padding: 20px; text-align: center; color: #666; font-size: 14px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏯 Ryokan Availability Alert</h1>
                    <p>New accommodation availability found in Shirakawa-go</p>
                </div>
                <div class="content">
                    <p>Great news! We found <strong>{count}</strong> accommodation(s) with availability for your target dates:</p>
        """.format(count=len(results))
        
        for result in results:
            html += f"""
                    <div class="accommodation">
                        <h3>{result.accommodation_name}</h3>
                        <div class="dates">
                            <strong>Available dates:</strong><br>
            """
            for date in result.available_dates:
                html += f'<span class="date">{date}</span>'
            
            html += f"""
                        </div>
                        <div class="link">
                            <a href="{result.url}" target="_blank">View Accommodation →</a>
                        </div>
                    </div>
            """
        
        html += """
                    <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #666;">
                        This is an automated notification from your Ryokan Availability Checker.
                    </p>
                </div>
                <div class="footer">
                    <p>🏯 Ryokan Tracker Dashboard</p>
                    <p>Monitoring Shirakawa-go accommodation availability</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_email_text(self, results: List) -> str:
        """Build plain text email content."""
        text = f"🏯 Ryokan Availability Alert\n\n"
        text += f"Great news! We found {len(results)} accommodation(s) with availability:\n\n"
        
        for i, result in enumerate(results, 1):
            text += f"{i}. {result.accommodation_name}\n"
            text += f"   Available dates: {', '.join(result.available_dates)}\n"
            text += f"   URL: {result.url}\n\n"
        
        text += "This is an automated notification from your Ryokan Availability Checker."
        
        return text
    
    async def test_endpoint(self) -> bool:
        """Test if notification endpoints are working."""
        # Test SendGrid if configured
        if self.sendgrid_client:
            try:
                # Just test if the client is properly initialized
                self.logger.info("SendGrid client is ready")
                sendgrid_ready = True
            except Exception as e:
                self.logger.error("SendGrid client test failed", error=str(e))
                sendgrid_ready = False
        else:
            sendgrid_ready = False
        
        # Test HTTP endpoint
        try:
            test_payload = {"message": "Test notification", "results": []}
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)) as session:
                async with session.post(self.endpoint_url, json=test_payload) as response:
                    http_ready = response.status == 200
                    self.logger.info("HTTP endpoint test", status=response.status, ready=http_ready)
        except Exception as e:
            self.logger.error("HTTP endpoint test failed", error=str(e))
            http_ready = False
        
        return sendgrid_ready or http_ready