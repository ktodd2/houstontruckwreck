import smtplib
import ssl
import csv
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import pytz
import logging
import urllib.parse
from models import Database, Subscriber, SentAlert, Incident
from config import Config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.db = Database()
        self.smtp_server = Config.EMAIL_HOST
        self.smtp_port = Config.EMAIL_PORT
        self.username = Config.EMAIL_USERNAME
        self.password = Config.EMAIL_PASSWORD
        self.from_email = Config.EMAIL_FROM
        # Set up Central Time timezone
        self.central_tz = pytz.timezone('America/Chicago')
    
    def get_central_time(self):
        """Get current time in Central Time"""
        return datetime.now(self.central_tz)
    
    def format_central_time(self, dt=None):
        """Format datetime in Central Time"""
        if dt is None:
            dt = self.get_central_time()
        return dt.strftime('%Y-%m-%d %I:%M:%S %p CST')
    
    def create_html_email(self, incidents):
        """Create HTML email content for incidents"""
        
        # Determine email subject based on incident types
        has_spill = any('spill' in inc[0].description.lower() or 'hazmat' in inc[0].description.lower() for inc in incidents)
        has_accident = any('accident' in inc[0].description.lower() or 'crash' in inc[0].description.lower() for inc in incidents)
        
        if has_spill and has_accident:
            subject = "🚨 CRITICAL ALERT: Spill & Accident in Houston!"
        elif has_spill:
            subject = "⚠️ SPILL ALERT: Hazardous Material Incident in Houston!"
        elif has_accident:
            subject = "🚨 ACCIDENT ALERT: Heavy Truck Incident in Houston!"
        else:
            subject = "🚛 Heavy Truck Incident Alert - Houston"
        
        # Create incident table HTML
        table_rows = ""
        for incident, incident_id in incidents:
            # Color coding based on severity
            if incident.severity >= 4:
                bg_color = "#ffcccc"  # Red for high severity
            elif incident.severity >= 3:
                bg_color = "#ffe6cc"  # Orange for medium severity
            else:
                bg_color = "#ffffff"  # White for low severity
            
            # Create Google Maps link
            location_query = urllib.parse.quote(f"{incident.location} Houston TX")
            maps_link = f"https://www.google.com/maps/search/?api=1&query={location_query}"
            
            table_rows += f"""
            <tr style="background-color: {bg_color};">
                <td style="padding: 12px; border: 1px solid #ddd;">
                    <a href="{maps_link}" target="_blank" style="color: #007bff; text-decoration: none;">
                        {incident.location}
                    </a>
                </td>
                <td style="padding: 12px; border: 1px solid #ddd;">{incident.description}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{incident.incident_time}</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">
                    {'🔴' if incident.severity >= 4 else '🟡' if incident.severity >= 3 else '🟢'}
                </td>
            </tr>
            """
        
        # Create full HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Houston Traffic Alert</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #007bff;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 10px;
                }}
                .alert-info {{
                    background-color: #e7f3ff;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                    border-left: 4px solid #007bff;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #f8f9fa;
                    padding: 12px;
                    text-align: left;
                    border: 1px solid #ddd;
                    font-weight: bold;
                }}
                td {{
                    padding: 12px;
                    border: 1px solid #ddd;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
                .severity-legend {{
                    margin: 15px 0;
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 5px;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="https://iili.io/FHbRMKu.png" alt="Houston Traffic Monitor Logo" style="max-width: 200px; height: auto; margin-bottom: 10px;"><br>
                    <div class="logo">Houston Traffic Monitor</div>
                    <div>Heavy Truck & Hazmat Incident Alert System</div>
                </div>
                
                <div class="alert-info">
                    <strong>📊 Alert Summary:</strong><br>
                    {len(incidents)} new incident(s) detected at {self.format_central_time()}<br>
                    Source: Houston TranStar Traffic Management
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>📍 Location</th>
                            <th>📝 Description</th>
                            <th>🕐 Time</th>
                            <th>⚠️ Priority</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                
                <div class="severity-legend">
                    <strong>Priority Legend:</strong>
                    🔴 High Priority (Spills, Major Accidents) | 
                    🟡 Medium Priority (Accidents, Blockages) | 
                    🟢 Low Priority (Stalls, Minor Incidents)
                </div>
                
                <div class="footer">
                    <strong>Houston Traffic Monitor</strong><br>
                    Automated monitoring system for heavy truck incidents and hazmat spills<br>
                    Data source: Houston TranStar | Generated: {self.format_central_time()}
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, html_content
    
    def create_text_email(self, incidents):
        """Create plain text email content for incidents"""
        text_content = f"""
HOUSTON TRAFFIC ALERT - {self.format_central_time()}

{len(incidents)} new heavy truck/hazmat incident(s) detected:

"""
        
        for i, (incident, incident_id) in enumerate(incidents, 1):
            priority = "HIGH" if incident.severity >= 4 else "MEDIUM" if incident.severity >= 3 else "LOW"
            text_content += f"""
Incident #{i}:
Location: {incident.location}
Description: {incident.description}
Time: {incident.incident_time}
Priority: {priority}
Google Maps: https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(f"{incident.location} Houston TX")}

{'-' * 60}
"""
        
        text_content += f"""

Data Source: Houston TranStar Traffic Management
System: Houston Traffic Monitor
Generated: {self.format_central_time()}
        """
        
        return text_content
    
    def send_alert(self, incidents):
        """Send email alert for new incidents"""
        if not incidents:
            logger.info("No incidents to send alerts for")
            return False
        
        # Check rate limiting
        recent_alerts = SentAlert.get_recent_count(self.db, hours=1)
        if recent_alerts >= Config.MAX_ALERTS_PER_HOUR:
            logger.warning(f"Rate limit exceeded: {recent_alerts} alerts sent in last hour")
            return False
        
        # Get active subscribers
        subscribers = Subscriber.get_all_active(self.db)
        if not subscribers:
            logger.warning("No active subscribers to send alerts to")
            return False
        
        # Validate email configuration
        if not all([self.username, self.password, self.from_email]):
            logger.error("Email configuration incomplete")
            return False
        
        try:
            # Create email content
            subject, html_content = self.create_html_email(incidents)
            text_content = self.create_text_email(incidents)
            
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(subscribers)
            
            # Attach both text and HTML versions
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            # Mark incidents as sent
            for incident, incident_id in incidents:
                SentAlert.mark_sent(self.db, incident_id)
            
            logger.info(f"✅ Alert sent successfully to {len(subscribers)} subscribers for {len(incidents)} incidents")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Email authentication failed - check username/password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}")
            return False
    
    def send_test_email(self, test_email):
        """Send a test email to verify configuration"""
        try:
            subject = "🧪 Houston Traffic Monitor - Test Email"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; }}
                    .header {{ text-align: center; color: #007bff; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="https://iili.io/FHbRMKu.png" alt="Houston Traffic Monitor Logo" style="max-width: 150px; height: auto; margin-bottom: 10px;"><br>
                        <h2>Houston Traffic Monitor</h2>
                        <h3>Test Email Successful!</h3>
                    </div>
                    <p>This is a test email to verify that your Houston Traffic Monitor email system is working correctly.</p>
                    <p><strong>System Status:</strong> ✅ Email service operational</p>
                    <p><strong>Test Time:</strong> {self.format_central_time()}</p>
                    <p>You will receive alerts when heavy truck incidents or hazmat spills are detected in the Houston area.</p>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
Houston Traffic Monitor - Test Email

This is a test email to verify that your Houston Traffic Monitor email system is working correctly.

System Status: Email service operational
Test Time: {self.format_central_time()}

You will receive alerts when heavy truck incidents or hazmat spills are detected in the Houston area.
            """
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = test_email
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"✅ Test email sent successfully to {test_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send test email: {e}")
            return False

    def send_daily_summary(self):
        """Send a daily CSV summary of incidents from the last 24 hours."""
        if not all([self.username, self.password, self.from_email]):
            logger.error("Email configuration incomplete")
            return False

        summary_email = Config.DAILY_SUMMARY_EMAIL
        if not summary_email:
            logger.error("Daily summary email not configured")
            return False

        incidents = Incident.get_recent(self.db, hours=24)
        csv_content = self._build_incident_csv(incidents)

        subject = "📊 Daily Summary: Houston Traffic Monitor (Last 24 Hours)"
        text_content = (
            f"Houston Traffic Monitor - Daily Summary\n\n"
            f"Incidents in the last 24 hours: {len(incidents)}\n"
            f"Generated: {self.format_central_time()}\n"
        )

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = summary_email

        msg.attach(MIMEText(text_content, "plain"))

        attachment = MIMEBase("text", "csv")
        attachment.set_payload(csv_content.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename="houston_traffic_daily_summary.csv",
        )
        msg.attach(attachment)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info("✅ Daily summary email sent successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send daily summary email: {e}")
            return False

    def _build_incident_csv(self, incidents):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Location", "Description", "Incident Time", "Scraped At", "Severity"])
        for incident in incidents:
            writer.writerow([
                incident["id"],
                incident["location"],
                incident["description"],
                incident["incident_time"],
                incident["scraped_at"],
                incident["severity"],
            ])
        return output.getvalue()

def test_email_service():
    """Test function for email service"""
    from models import Incident
    
    # Create test incidents
    test_incidents = [
        (Incident("I-45 at Beltway 8", "Semi-truck accident blocking left lane", "14:30", 3), 1),
        (Incident("US-59 near Downtown", "Hazmat spill - chemical leak from truck", "14:35", 5), 2)
    ]
    
    email_service = EmailService()
    success = email_service.send_alert(test_incidents)
    
    if success:
        print("✅ Test email sent successfully!")
    else:
        print("❌ Test email failed!")

if __name__ == "__main__":
    test_email_service()
