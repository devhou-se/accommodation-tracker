import requests
from typing import List
from datetime import datetime
from .config import EmailConfig
from .plugins.base import CheckResult, TicketAvailability


class EmailService:
    """Service for sending email notifications via Mailgun"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.api_url = f"https://api.mailgun.net/v3/{config.domain}/messages"
    
    async def send_availability_notification(self, result: CheckResult) -> bool:
        """Send email notification about ticket availability"""
        try:
            subject = self._create_subject(result)
            html_body = self._create_html_body(result)
            text_body = self._create_text_body(result)
            
            # Send to all recipients
            for recipient in self.config.recipients:
                success = await self._send_email(
                    to=recipient,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body
                )
                if not success:
                    print(f"Failed to send email to {recipient}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error sending email notification: {e}")
            return False
    
    async def _send_email(self, to: str, subject: str, text_body: str, html_body: str) -> bool:
        """Send individual email via Mailgun API"""
        try:
            data = {
                "from": self.config.from_email,
                "to": to,
                "subject": subject,
                "text": text_body,
                "html": html_body
            }
            
            response = requests.post(
                self.api_url,
                auth=("api", self.config.api_key),
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"Email sent successfully to {to}")
                return True
            else:
                print(f"Failed to send email to {to}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending email to {to}: {e}")
            return False
    
    def _create_subject(self, result: CheckResult) -> str:
        """Create email subject line"""
        if not result.success:
            return f"❌ Error checking {result.event_name}"
        
        available_count = len([a for a in result.availabilities if a.status == "available"])
        if available_count > 0:
            return f"🎫 Tickets Available: {result.event_name}"
        else:
            return f"ℹ️ Status Update: {result.event_name}"
    
    def _create_html_body(self, result: CheckResult) -> str:
        """Create HTML email body"""
        if not result.success:
            return f"""
            <html>
            <body>
                <h2>❌ Error Checking Tickets</h2>
                <p><strong>Event:</strong> {result.event_name}</p>
                <p><strong>Plugin:</strong> {result.plugin_name}</p>
                <p><strong>Check Time:</strong> {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Error:</strong> {result.error_message}</p>
            </body>
            </html>
            """
        
        html = f"""
        <html>
        <body>
            <h2>🎫 Ticket Availability Report</h2>
            <p><strong>Event:</strong> {result.event_name}</p>
            <p><strong>Check Time:</strong> {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Availability Status:</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th style="padding: 8px;">Date</th>
                    <th style="padding: 8px;">Seat Type</th>
                    <th style="padding: 8px;">Status</th>
                    <th style="padding: 8px;">Price/Info</th>
                    <th style="padding: 8px;">Action</th>
                </tr>
        """
        
        for availability in result.availabilities:
            status_emoji = self._get_status_emoji(availability.status)
            booking_link = ""
            if availability.booking_url:
                booking_link = f'<a href="{availability.booking_url}" style="background-color: #4CAF50; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">Book Now</a>'
            
            html += f"""
                <tr>
                    <td style="padding: 8px;">{availability.date}</td>
                    <td style="padding: 8px;">{availability.seat_type}</td>
                    <td style="padding: 8px;">{status_emoji} {availability.status.replace('_', ' ').title()}</td>
                    <td style="padding: 8px;">{availability.price or 'N/A'}</td>
                    <td style="padding: 8px;">{booking_link}</td>
                </tr>
            """
        
        html += """
            </table>
            <br>
            <p><em>This is an automated notification from the Ticket Availability Tracker.</em></p>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_body(self, result: CheckResult) -> str:
        """Create plain text email body"""
        if not result.success:
            return f"""
Error Checking Tickets

Event: {result.event_name}
Plugin: {result.plugin_name}
Check Time: {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}
Error: {result.error_message}
            """
        
        text = f"""
Ticket Availability Report

Event: {result.event_name}
Check Time: {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}

Availability Status:
"""
        
        for availability in result.availabilities:
            status_text = availability.status.replace('_', ' ').title()
            text += f"""
- Date: {availability.date}
  Seat Type: {availability.seat_type}
  Status: {status_text}
  Price/Info: {availability.price or 'N/A'}
"""
            if availability.booking_url:
                text += f"  Booking URL: {availability.booking_url}\n"
        
        text += "\nThis is an automated notification from the Ticket Availability Tracker."
        return text
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        emoji_map = {
            "available": "✅",
            "limited": "⚠️", 
            "sold_out": "❌",
            "not_on_sale": "⏳"
        }
        return emoji_map.get(status, "ℹ️")