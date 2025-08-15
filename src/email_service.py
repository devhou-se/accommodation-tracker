import requests
from typing import List
from datetime import datetime
from .config import EmailConfig
from .plugins.base import CheckResult, BookingAvailability


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
            return f"🤖 Slop Bot - Error checking {result.item_name}"
        
        available_count = len([a for a in result.availabilities if a.status == "available"])
        if available_count > 0:
            return f"🤖 Slop Bot - Availability Found: {result.item_name}"
        else:
            return f"🤖 Slop Bot - Status Update: {result.item_name}"
    
    def _create_html_body(self, result: CheckResult) -> str:
        """Create HTML email body"""
        if not result.success:
            return f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>🤖 Slop Bot - Error Report</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #333;
                        min-height: 100vh;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 16px;
                        padding: 30px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                    }}
                    h1 {{
                        color: #2c3e50;
                        font-size: 1.8rem;
                        font-weight: 700;
                        text-align: center;
                        margin-bottom: 25px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    .error-card {{
                        background: linear-gradient(145deg, #f8d7da, #f5c6cb);
                        border-radius: 12px;
                        padding: 20px;
                        border-left: 4px solid #dc3545;
                    }}
                    p {{
                        margin: 10px 0;
                        line-height: 1.5;
                    }}
                    strong {{
                        color: #2c3e50;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 Slop Bot - Error Report</h1>
                    <div class="error-card">
                        <p><strong>Item:</strong> {result.item_name}</p>
                        <p><strong>Plugin:</strong> {result.plugin_name}</p>
                        <p><strong>Check Time:</strong> {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p><strong>Error:</strong> {result.error_message}</p>
                    </div>
                </div>
            </body>
            </html>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🤖 Slop Bot - Availability Monitor</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 16px;
                    padding: 30px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    font-size: 1.8rem;
                    font-weight: 700;
                    text-align: center;
                    margin-bottom: 25px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }}
                h2 {{
                    color: #2c3e50;
                    font-size: 1.3rem;
                    font-weight: 600;
                    margin-bottom: 15px;
                }}
                .info-card {{
                    background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border-left: 4px solid #28a745;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #2c3e50;
                }}
                .availability-status {{
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                }}
                .available {{
                    background: linear-gradient(135deg, #10b981, #059669);
                    color: white;
                }}
                .available::before {{
                    content: '✓';
                    font-size: 10px;
                }}
                .limited {{
                    background: linear-gradient(135deg, #f59e0b, #d97706);
                    color: white;
                }}
                .limited::before {{
                    content: '⚠';
                    font-size: 10px;
                }}
                .sold-out {{
                    background: linear-gradient(135deg, #ef4444, #dc2626);
                    color: white;
                }}
                .sold-out::before {{
                    content: '✕';
                    font-size: 10px;
                }}
                .not-on-sale {{
                    background: linear-gradient(135deg, #6b7280, #4b5563);
                    color: white;
                }}
                .not-on-sale::before {{
                    content: '◐';
                    font-size: 10px;
                }}
                .btn {{
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 20px;
                    text-decoration: none;
                    font-size: 12px;
                    font-weight: 600;
                    display: inline-block;
                }}
                p {{
                    margin: 10px 0;
                    line-height: 1.5;
                }}
                strong {{
                    color: #2c3e50;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    font-style: italic;
                    color: #6c757d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Slop Bot - Availability Monitor 🎯</h1>
                <div class="info-card">
                    <p><strong>Item:</strong> {result.item_name}</p>
                    <p><strong>Check Time:</strong> {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h2>Availabilities</h2>
                <table>
                    <tr>
                        <th>Date</th>
                        <th>Room Type</th>
                        <th>Status</th>
                        <th>Price/Info</th>
                        <th>Action</th>
                    </tr>
        """
        
        for availability in result.availabilities:
            status_emoji = self._get_status_emoji(availability.status)
            booking_link = ""
            if availability.booking_url:
                booking_link = f'<a href="{availability.booking_url}" style="background-color: #4CAF50; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px;">Book Now</a>'
            
            venue_info = f" - {availability.venue}" if availability.venue else ""
            html += f"""
                <tr>
                    <td>{availability.date}</td>
                    <td>{availability.room_type}{venue_info}</td>
                    <td><span class="availability-status {availability.status.replace('_', '-')}">{availability.status.replace('_', ' ').title()}</span></td>
                    <td>{availability.price or 'N/A'}</td>
                    <td>{booking_link}</td>
                </tr>
            """
        
        html += """
                </table>
                <div class="footer">
                    <p>This is an automated notification from the Availability Tracker.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_text_body(self, result: CheckResult) -> str:
        """Create plain text email body"""
        if not result.success:
            return f"""
🤖 Slop Bot - Error Report

Item: {result.item_name}
Plugin: {result.plugin_name}
Check Time: {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}
Error: {result.error_message}
            """
        
        text = f"""
🤖 Slop Bot - Availability Monitor 🎯

Item: {result.item_name}
Check Time: {result.check_time.strftime('%Y-%m-%d %H:%M:%S')}

Availabilities:
"""
        
        for availability in result.availabilities:
            status_text = availability.status.replace('_', ' ').title()
            venue_info = f" - {availability.venue}" if availability.venue else ""
            text += f"""
- Date: {availability.date}
  Room Type: {availability.room_type}{venue_info}
  Status: {status_text}
  Price/Info: {availability.price or 'N/A'}
"""
            if availability.booking_url:
                text += f"  Booking URL: {availability.booking_url}\n"
        
        text += "\nThis is an automated notification from the Availability Tracker."
        return text
    
    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status - matches webpage styling"""
        emoji_map = {
            "available": "✓",
            "limited": "⚠",
            "sold_out": "✕",
            "not_on_sale": "◐",
            "error": "!",
            "unknown": "?"
        }
        return emoji_map.get(status, "?")