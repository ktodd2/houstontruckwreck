import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import pytz
import logging
import urllib.parse
import csv
import io
import base64
import os
from models import Database, Subscriber, HazmatSubscriber, SentAlert, Incident
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
        # Load and encode logo image
        self.logo_base64 = self._load_logo()
    
    def _load_logo(self):
        """Load and encode the logo image as base64"""
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'truckwreck.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                return f"data:image/png;base64,{encoded_string}"
            else:
                logger.warning(f"Logo file not found at {logo_path}")
                return ""
        except Exception as e:
            logger.error(f"Error loading logo: {e}")
            return ""
    
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
            
            # Create Google Maps link - replace "at" with "and" for better intersection recognition
            location_formatted = incident.location.replace(' at ', ' and ').replace(' AT ', ' and ')
            location_query = urllib.parse.quote(f"{location_formatted} Houston TX")
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
                    <img src="{self.logo_base64}" alt="Houston Traffic Monitor Logo" style="max-width: 200px; height: auto; margin-bottom: 10px;"><br>
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
            # Replace "at" with "and" for better intersection recognition
            location_formatted = incident.location.replace(' at ', ' and ').replace(' AT ', ' and ')
            text_content += f"""
Incident #{i}:
Location: {incident.location}
Description: {incident.description}
Time: {incident.incident_time}
Priority: {priority}
Google Maps: https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(f"{location_formatted} Houston TX")}

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
    
    def send_hazmat_alert(self, incidents):
        """Send email alert for hazmat/spill incidents only to hazmat subscribers"""
        if not incidents:
            logger.info("No hazmat incidents to send alerts for")
            return False
        
        # Filter for only hazmat/spill incidents
        hazmat_incidents = []
        for incident, incident_id in incidents:
            desc_lower = incident.description.lower()
            if 'hazmat' in desc_lower or 'spill' in desc_lower:
                hazmat_incidents.append((incident, incident_id))
        
        if not hazmat_incidents:
            logger.info("No hazmat/spill incidents found")
            return False
        
        # Get active hazmat subscribers
        hazmat_subscribers = HazmatSubscriber.get_all_active(self.db)
        if not hazmat_subscribers:
            logger.info("No active hazmat subscribers to send alerts to")
            return False
        
        # Validate email configuration
        if not all([self.username, self.password, self.from_email]):
            logger.error("Email configuration incomplete")
            return False
        
        try:
            # Create email content with hazmat-specific branding
            subject = f"☣️ HAZMAT ALERT: {len(hazmat_incidents)} Spill/Hazmat Incident{'s' if len(hazmat_incidents) != 1 else ''} in Houston!"
            
            # Create incident table HTML
            table_rows = ""
            for incident, incident_id in hazmat_incidents:
                bg_color = "#ffcccc"  # Red for hazmat incidents
                location_formatted = incident.location.replace(' at ', ' and ').replace(' AT ', ' and ')
                location_query = urllib.parse.quote(f"{location_formatted} Houston TX")
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
                </tr>
                """
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Houston Hazmat Alert</title>
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
                        border-bottom: 3px solid #dc3545;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #dc3545;
                        margin-bottom: 10px;
                    }}
                    .alert-info {{
                        background-color: #fff3cd;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 20px;
                        border-left: 4px solid #dc3545;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                    }}
                    th {{
                        background-color: #dc3545;
                        color: white;
                        padding: 12px;
                        text-align: left;
                        border: 1px solid #bd2130;
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
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="{self.logo_base64}" alt="Houston Traffic Monitor Logo" style="max-width: 200px; height: auto; margin-bottom: 10px;"><br>
                        <div class="logo">☣️ HAZMAT ALERT SYSTEM</div>
                        <div>Hazardous Material & Spill Monitoring</div>
                    </div>
                    
                    <div class="alert-info">
                        <strong>⚠️ CRITICAL HAZMAT ALERT:</strong><br>
                        {len(hazmat_incidents)} hazmat/spill incident(s) detected at {self.format_central_time()}<br>
                        <strong>Immediate attention required</strong><br>
                        Source: Houston TranStar Traffic Management
                    </div>
                    
                    <table>
                        <thead>
                            <tr>
                                <th>📍 Location</th>
                                <th>📝 Description</th>
                                <th>🕐 Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <strong>Houston Traffic Monitor - Hazmat Alert System</strong><br>
                        Specialized monitoring for hazardous material spills and incidents<br>
                        Data source: Houston TranStar | Generated: {self.format_central_time()}<br>
                        <br>
                        <em>You are receiving this because you subscribed to hazmat-only alerts</em>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create text version
            text_content = f"""
HOUSTON HAZMAT ALERT - {self.format_central_time()}

⚠️ CRITICAL: {len(hazmat_incidents)} hazmat/spill incident(s) detected:

"""
            
            for i, (incident, incident_id) in enumerate(hazmat_incidents, 1):
                location_formatted = incident.location.replace(' at ', ' and ').replace(' AT ', ' and ')
                text_content += f"""
Hazmat Incident #{i}:
Location: {incident.location}
Description: {incident.description}
Time: {incident.incident_time}
Google Maps: https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(f"{location_formatted} Houston TX")}

{'-' * 60}
"""
            
            text_content += f"""

Data Source: Houston TranStar Traffic Management
System: Houston Traffic Monitor - Hazmat Alert System
Generated: {self.format_central_time()}

You are receiving this because you subscribed to hazmat-only alerts.
            """
            
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(hazmat_subscribers)
            
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
            
            logger.info(f"Hazmat alert sent successfully to {len(hazmat_subscribers)} hazmat subscribers for {len(hazmat_incidents)} incidents")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email authentication failed - check username/password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending hazmat email: {e}")
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
                        <img src="{self.logo_base64}" alt="Houston Traffic Monitor Logo" style="max-width: 150px; height: auto; margin-bottom: 10px;"><br>
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
    
    def generate_csv_data(self, incidents):
        """Generate CSV data from incidents"""
        output = io.StringIO()
        csv_writer = csv.writer(output)
        
        # Write header
        csv_writer.writerow(['Date', 'Time', 'Location', 'Description', 'Severity', 'Scraped At'])
        
        # Write incident data
        for incident in incidents:
            # Parse scraped_at timestamp
            scraped_at = incident['scraped_at']
            
            csv_writer.writerow([
                scraped_at.split()[0] if ' ' in scraped_at else scraped_at,  # Date
                incident['incident_time'],  # Time
                incident['location'],  # Location
                incident['description'],  # Description
                'High' if incident['severity'] >= 4 else 'Medium' if incident['severity'] >= 3 else 'Low',  # Severity
                scraped_at  # Scraped At
            ])
        
        return output.getvalue()
    
    def create_daily_summary_html(self, incidents_data, date_str):
        """Create HTML email content for daily summary"""
        
        total_incidents = len(incidents_data)
        
        # Categorize incidents
        wrecks = [i for i in incidents_data if 'accident' in i['description'].lower() or 'crash' in i['description'].lower() or 'wreck' in i['description'].lower()]
        stalls = [i for i in incidents_data if 'stall' in i['description'].lower()]
        spills = [i for i in incidents_data if 'spill' in i['description'].lower() or 'hazmat' in i['description'].lower()]
        other = [i for i in incidents_data if i not in wrecks and i not in stalls and i not in spills]
        
        # Create incident table HTML
        table_rows = ""
        for incident in incidents_data:
            # Color coding based on severity
            if incident['severity'] >= 4:
                bg_color = "#ffcccc"  # Red for high severity
            elif incident['severity'] >= 3:
                bg_color = "#ffe6cc"  # Orange for medium severity
            else:
                bg_color = "#ffffff"  # White for low severity
            
            # Create Google Maps link - replace "at" with "and" for better intersection recognition
            location_formatted = incident['location'].replace(' at ', ' and ').replace(' AT ', ' and ')
            location_query = urllib.parse.quote(f"{location_formatted} Houston TX")
            maps_link = f"https://www.google.com/maps/search/?api=1&query={location_query}"
            
            # Determine incident type icon
            if 'accident' in incident['description'].lower() or 'crash' in incident['description'].lower() or 'wreck' in incident['description'].lower():
                icon = "🚗💥"
            elif 'stall' in incident['description'].lower():
                icon = "🚛"
            elif 'spill' in incident['description'].lower() or 'hazmat' in incident['description'].lower():
                icon = "☣️"
            else:
                icon = "⚠️"
            
            table_rows += f"""
            <tr style="background-color: {bg_color};">
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{icon}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">
                    <a href="{maps_link}" target="_blank" style="color: #007bff; text-decoration: none;">
                        {incident['location']}
                    </a>
                </td>
                <td style="padding: 12px; border: 1px solid #ddd;">{incident['description']}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{incident['incident_time']}</td>
            </tr>
            """
        
        # Create full HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Houston Traffic Daily Summary</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 3px solid #007bff;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 10px;
                }}
                .summary-box {{
                    display: flex;
                    justify-content: space-around;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }}
                .summary-item {{
                    text-align: center;
                    padding: 20px;
                    margin: 10px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    min-width: 150px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .summary-number {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #007bff;
                }}
                .summary-label {{
                    font-size: 14px;
                    color: #666;
                    margin-top: 5px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 25px 0;
                }}
                th {{
                    background-color: #007bff;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    border: 1px solid #0056b3;
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
                    border-top: 2px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
                .no-incidents {{
                    text-align: center;
                    padding: 40px;
                    font-size: 18px;
                    color: #28a745;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{self.logo_base64}" alt="Houston Traffic Monitor Logo" style="max-width: 200px; height: auto; margin-bottom: 10px;"><br>
                    <div class="logo">📊 Daily Traffic Summary</div>
                    <div style="font-size: 18px; color: #666;">Houston Heavy Truck & Hazmat Incidents</div>
                    <div style="font-size: 14px; color: #999; margin-top: 10px;">{date_str}</div>
                </div>
                
                <div class="summary-box">
                    <div class="summary-item">
                        <div class="summary-number">{total_incidents}</div>
                        <div class="summary-label">Total Incidents</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-number" style="color: #dc3545;">{len(wrecks)}</div>
                        <div class="summary-label">🚗 Wrecks/Accidents</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-number" style="color: #ffc107;">{len(stalls)}</div>
                        <div class="summary-label">🚛 Stalls</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-number" style="color: #ff6b6b;">{len(spills)}</div>
                        <div class="summary-label">☣️ Hazmat/Spills</div>
                    </div>
                </div>
                
                {"<div class='no-incidents'>✅ Great news! No incidents were reported today.</div>" if total_incidents == 0 else f'''
                <h3 style="color: #007bff; border-bottom: 2px solid #e9ecef; padding-bottom: 10px;">Detailed Incident Report</h3>
                <p style="color: #666; font-size: 14px;">See attached CSV file for complete data that can be imported into spreadsheets.</p>
                
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: center;">Type</th>
                            <th>📍 Location</th>
                            <th>📝 Description</th>
                            <th>🕐 Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
                '''}
                
                <div class="footer">
                    <strong>Houston Traffic Monitor</strong><br>
                    Daily automated summary of heavy truck incidents and hazmat spills<br>
                    Data source: Houston TranStar Traffic Management<br>
                    Report generated: {self.format_central_time()}<br>
                    <br>
                    <em>This is an automated daily report sent at midnight CST</em>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_daily_summary(self, target_email="ktoddllc1@gmail.com"):
        """Send daily summary email at midnight with CSV attachment"""
        try:
            # Get yesterday's date (since this runs at midnight)
            yesterday = self.get_central_time() - timedelta(days=1)
            date_str = yesterday.strftime('%B %d, %Y')  # e.g., "January 7, 2026"
            
            # Get incidents from the past 24 hours
            incidents = Incident.get_recent(self.db, hours=24)
            
            # Convert to list of dicts for easier processing
            incidents_data = []
            for incident in incidents:
                incidents_data.append({
                    'id': incident['id'],
                    'location': incident['location'],
                    'description': incident['description'],
                    'incident_time': incident['incident_time'],
                    'scraped_at': incident['scraped_at'],
                    'severity': incident['severity']
                })
            
            total_count = len(incidents_data)
            
            # Create email subject
            if total_count == 0:
                subject = f"📊 Daily Summary - {date_str} - No Incidents ✅"
            else:
                subject = f"📊 Daily Summary - {date_str} - {total_count} Incident{'s' if total_count != 1 else ''}"
            
            # Create HTML content
            html_content = self.create_daily_summary_html(incidents_data, date_str)
            
            # Create text content
            text_content = f"""
HOUSTON TRAFFIC MONITOR - DAILY SUMMARY
{date_str}
{'=' * 60}

Total Incidents: {total_count}

"""
            
            if total_count > 0:
                for i, incident in enumerate(incidents_data, 1):
                    text_content += f"""
Incident #{i}:
Location: {incident['location']}
Description: {incident['description']}
Time: {incident['incident_time']}
Scraped: {incident['scraped_at']}

{'-' * 60}
"""
            else:
                text_content += "✅ Great news! No incidents were reported today.\n\n"
            
            text_content += f"""

Data Source: Houston TranStar Traffic Management
System: Houston Traffic Monitor
Report Generated: {self.format_central_time()}

This is an automated daily report sent at midnight CST.
            """
            
            # Create email message
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = target_email
            
            # Create alternative part for text and HTML
            msg_alternative = MIMEMultipart("alternative")
            msg_alternative.attach(MIMEText(text_content, "plain"))
            msg_alternative.attach(MIMEText(html_content, "html"))
            msg.attach(msg_alternative)
            
            # Attach CSV file if there are incidents
            if total_count > 0:
                csv_data = self.generate_csv_data(incidents)
                
                csv_attachment = MIMEBase('text', 'csv')
                csv_attachment.set_payload(csv_data.encode('utf-8'))
                encoders.encode_base64(csv_attachment)
                
                # Create filename with date
                csv_filename = f"houston_traffic_incidents_{yesterday.strftime('%Y-%m-%d')}.csv"
                csv_attachment.add_header('Content-Disposition', f'attachment; filename="{csv_filename}"')
                msg.attach(csv_attachment)
            
            # Validate email configuration
            if not all([self.username, self.password, self.from_email]):
                logger.error("Email configuration incomplete")
                return False
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"✅ Daily summary sent successfully to {target_email} - {total_count} incidents")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Email authentication failed - check username/password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending daily summary: {e}")
            return False

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
