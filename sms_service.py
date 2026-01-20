import logging
from datetime import datetime
import pytz
import requests
from models import Database, Subscriber, HazmatSubscriber, SentSMSAlert
from config import Config

logger = logging.getLogger(__name__)


class SMSService:
    def __init__(self):
        self.db = Database()
        self.central_tz = pytz.timezone('America/Chicago')
        self.api_key = Config.TELNYX_API_KEY
        self.from_number = Config.TELNYX_FROM_NUMBER
        self.api_url = "https://api.telnyx.com/v2/messages"

    def get_central_time(self):
        """Get current time in Central Time"""
        return datetime.now(self.central_tz)

    def format_central_time(self, dt=None):
        """Format datetime in Central Time"""
        if dt is None:
            dt = self.get_central_time()
        return dt.strftime('%I:%M %p CST')

    def is_configured(self):
        """Check if SMS service is properly configured"""
        return bool(Config.SMS_ENABLED and Config.TELNYX_API_KEY and Config.TELNYX_FROM_NUMBER)

    def format_sms_message(self, incidents):
        """Format incidents into SMS message (160 char limit)"""
        count = len(incidents)

        if count == 1:
            incident = incidents[0][0]
            # Single incident - include more detail
            location = incident.location[:40] if len(incident.location) > 40 else incident.location
            desc = incident.description[:50] if len(incident.description) > 50 else incident.description
            msg = f"HOUSTON ALERT: {location} - {desc}"
        else:
            # Multiple incidents - summarize
            locations = [inc[0].location.split('@')[0].strip()[:20] for inc in incidents[:3]]
            loc_str = ', '.join(locations)
            if count > 3:
                loc_str += f" +{count - 3} more"
            msg = f"HOUSTON ALERT: {count} incidents - {loc_str}"

        # Truncate to 160 chars
        if len(msg) > 157:
            msg = msg[:157] + "..."

        return msg

    def format_hazmat_sms_message(self, incidents):
        """Format hazmat incidents into SMS message"""
        count = len(incidents)

        if count == 1:
            incident = incidents[0][0]
            location = incident.location[:35] if len(incident.location) > 35 else incident.location
            msg = f"HAZMAT ALERT: {location} - Spill/hazmat incident reported"
        else:
            msg = f"HAZMAT ALERT: {count} spill/hazmat incidents in Houston area"

        # Truncate to 160 chars
        if len(msg) > 157:
            msg = msg[:157] + "..."

        return msg

    def send_sms(self, to_number, message):
        """Send a single SMS via Telnyx REST API"""
        if not self.is_configured():
            logger.warning("SMS service not configured - skipping send")
            return False

        try:
            # Format phone number (ensure it has +1 prefix for US)
            if not to_number.startswith('+'):
                to_number = '+1' + to_number.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }

            payload = {
                'from': self.from_number,
                'to': to_number,
                'text': message
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

            if response.status_code in [200, 201, 202]:
                logger.info(f"SMS sent successfully to {to_number}")
                return True
            else:
                logger.error(f"Telnyx API error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending SMS to {to_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {e}")
            return False

    def send_sms_alert(self, incidents):
        """Send SMS alerts for new incidents to all SMS-enabled subscribers"""
        if not incidents:
            logger.info("No incidents to send SMS alerts for")
            return False

        if not self.is_configured():
            logger.info("SMS service not configured - skipping alerts")
            return False

        # Check rate limiting
        recent_sms = SentSMSAlert.get_recent_count(self.db, hours=1)
        if recent_sms >= Config.SMS_MAX_ALERTS_PER_HOUR:
            logger.warning(f"SMS rate limit exceeded: {recent_sms} SMS sent in last hour")
            return False

        # Get SMS-enabled subscribers
        phone_numbers = Subscriber.get_all_sms_active(self.db)
        if not phone_numbers:
            logger.info("No SMS-enabled subscribers")
            return False

        # Format message
        message = self.format_sms_message(incidents)

        # Send to each subscriber
        success_count = 0
        for phone in phone_numbers:
            # Check per-phone rate limiting (don't spam same number)
            for incident, incident_id in incidents:
                if not SentSMSAlert.is_already_sent(self.db, incident_id, phone):
                    if self.send_sms(phone, message):
                        SentSMSAlert.mark_sent(self.db, incident_id, phone)
                        success_count += 1
                    break  # Only send one SMS per batch of incidents

        logger.info(f"SMS alerts sent to {success_count} subscribers for {len(incidents)} incidents")
        return success_count > 0

    def send_hazmat_sms_alert(self, incidents):
        """Send SMS alerts for hazmat incidents to hazmat SMS subscribers"""
        if not incidents:
            logger.info("No incidents for hazmat SMS alerts")
            return False

        if not self.is_configured():
            logger.info("SMS service not configured - skipping hazmat alerts")
            return False

        # Filter for only hazmat/spill incidents
        hazmat_incidents = []
        for incident, incident_id in incidents:
            desc_lower = incident.description.lower()
            if 'hazmat' in desc_lower or 'spill' in desc_lower:
                hazmat_incidents.append((incident, incident_id))

        if not hazmat_incidents:
            logger.info("No hazmat/spill incidents for SMS")
            return False

        # Get hazmat SMS-enabled subscribers
        phone_numbers = HazmatSubscriber.get_all_sms_active(self.db)
        if not phone_numbers:
            logger.info("No hazmat SMS-enabled subscribers")
            return False

        # Format message
        message = self.format_hazmat_sms_message(hazmat_incidents)

        # Send to each subscriber
        success_count = 0
        for phone in phone_numbers:
            for incident, incident_id in hazmat_incidents:
                if not SentSMSAlert.is_already_sent(self.db, incident_id, phone):
                    if self.send_sms(phone, message):
                        SentSMSAlert.mark_sent(self.db, incident_id, phone)
                        success_count += 1
                    break

        logger.info(f"Hazmat SMS alerts sent to {success_count} subscribers")
        return success_count > 0

    def send_test_sms(self, to_number):
        """Send a test SMS to verify configuration"""
        if not self.is_configured():
            logger.error("SMS service not configured")
            return False

        message = f"Houston Traffic Monitor - Test SMS sent at {self.format_central_time()}. SMS alerts are working!"

        return self.send_sms(to_number, message)


def test_sms_service():
    """Test function for SMS service"""
    from models import Incident

    # Create test incidents
    test_incidents = [
        (Incident("I-45 at Beltway 8", "Semi-truck accident blocking left lane", "14:30", 3), 1),
    ]

    sms_service = SMSService()

    print(f"SMS configured: {sms_service.is_configured()}")
    print(f"Test message: {sms_service.format_sms_message(test_incidents)}")


if __name__ == "__main__":
    test_sms_service()
