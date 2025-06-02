import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime
from models import Incident, Database
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranStarScraper:
    def __init__(self):
        self.url = Config.TRANSTAR_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.db = Database()
    
    def is_relevant_incident(self, text):
        """Check if incident involves heavy trucks or hazmat spills"""
        text_lower = text.lower()
        
        # Heavy truck keywords
        truck_keywords = [
            'heavy truck', 'semi', 'semi-truck', 'semi truck',
            '18-wheeler', '18 wheeler', 'eighteen wheeler',
            'tractor-trailer', 'tractor trailer', 'big rig',
            'commercial vehicle', 'freight truck', 'cargo truck',
            'delivery truck', 'box truck', 'flatbed truck'
        ]
        
        # Hazmat and spill keywords
        spill_keywords = [
            'hazmat', 'hazardous material', 'chemical spill',
            'fuel spill', 'oil spill', 'cargo spill',
            'debris spill', 'spill', 'leak', 'leaking'
        ]
        
        # Check for truck-related incidents
        has_truck = any(keyword in text_lower for keyword in truck_keywords)
        
        # Check for spill incidents (any vehicle type)
        has_spill = any(keyword in text_lower for keyword in spill_keywords)
        
        # Additional patterns for truck incidents
        truck_patterns = [
            r'\b(?:18|eighteen)[\s-]*wheel\w*\b',
            r'\btruck\s+(?:accident|crash|stall|breakdown|rollover)\b',
            r'\b(?:accident|crash)\s+.*\btruck\b',
            r'\bcommercial\s+vehicle\s+(?:accident|crash|stall)\b'
        ]
        
        has_pattern = any(re.search(pattern, text_lower) for pattern in truck_patterns)
        
        # Check if this is a stall incident
        is_stall = 'stall' in text_lower or 'breakdown' in text_lower
        
        # If stalls are disabled and this is a stall, exclude it
        from models import Settings
        if is_stall and not Settings.get_include_stalls(self.db):
            return False
        
        return has_truck or has_spill or has_pattern
    
    def extract_location(self, text):
        """Extract location from incident text"""
        # Common Houston highway patterns
        patterns = [
            r'(I-\d+[NSEW]?(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
            r'(US-\d+[NSEW]?(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
            r'(Highway\s+\d+(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
            r'(Beltway\s+8(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
            r'(\w+\s+Freeway(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
            r'(Loop\s+\d+(?:\s+(?:at|near|and)\s+[\w\s]+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback - look for any location-like text
        location_words = ['at', 'near', 'on', 'between']
        for word in location_words:
            if word in text.lower():
                parts = text.split(word, 1)
                if len(parts) > 1:
                    location = parts[1].strip()[:50]  # Limit length
                    if location:
                        return location
        
        return "Houston Area"
    
    def extract_time(self, text):
        """Extract time from incident text"""
        time_pattern = r'\d{1,2}:\d{2}(?:\s*[APap][Mm])?'
        match = re.search(time_pattern, text)
        
        if match:
            return match.group()
        else:
            return datetime.now().strftime("%H:%M")
    
    def calculate_severity(self, description):
        """Calculate incident severity (1-5, higher = more urgent)"""
        description_lower = description.lower()
        severity = 1
        
        # Spill incidents are highest priority
        if any(keyword in description_lower for keyword in ['hazmat', 'chemical', 'spill']):
            severity += 3
        
        # Accident severity
        if any(keyword in description_lower for keyword in ['accident', 'crash', 'collision']):
            severity += 2
        elif any(keyword in description_lower for keyword in ['rollover', 'jackknife']):
            severity += 3
        
        # Multiple vehicles
        if any(keyword in description_lower for keyword in ['multiple', 'multi-vehicle', 'pile-up']):
            severity += 1
        
        # Lane blockages
        if any(keyword in description_lower for keyword in ['blocked', 'blocking', 'closed']):
            severity += 1
        
        return min(severity, 5)  # Cap at 5
    
    def scrape_incidents(self):
        """Scrape incidents from TranStar website"""
        try:
            logger.info(f"Scraping incidents from {self.url}")
            
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for incident data in tables
            incidents = []
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:  # Need at least location and description
                        
                        # Extract text from all cells
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        full_text = " | ".join(cell_texts)
                        
                        # Check if this is a relevant incident
                        if self.is_relevant_incident(full_text):
                            
                            # Extract incident details
                            location = self.extract_location(cell_texts[0] if cell_texts[0] else full_text)
                            description = cell_texts[1] if len(cell_texts) > 1 else full_text
                            incident_time = self.extract_time(cell_texts[2] if len(cell_texts) > 2 else full_text)
                            severity = self.calculate_severity(description)
                            
                            # Clean up description
                            description = description[:200]  # Limit length
                            if not description:
                                description = "Heavy truck incident reported"
                            
                            incident = Incident(
                                location=location,
                                description=description,
                                incident_time=incident_time,
                                severity=severity
                            )
                            
                            incidents.append(incident)
            
            # Also look for incident data in divs and other elements
            incident_divs = soup.find_all(['div', 'span'], class_=re.compile(r'incident|alert|closure|traffic', re.I))
            
            for div in incident_divs:
                text = div.get_text(strip=True)
                if text and self.is_relevant_incident(text):
                    
                    location = self.extract_location(text)
                    description = text[:200]
                    incident_time = self.extract_time(text)
                    severity = self.calculate_severity(description)
                    
                    incident = Incident(
                        location=location,
                        description=description,
                        incident_time=incident_time,
                        severity=severity
                    )
                    
                    incidents.append(incident)
            
            logger.info(f"Found {len(incidents)} relevant incidents")
            return incidents
            
        except requests.RequestException as e:
            logger.error(f"Error scraping TranStar: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return []
    
    def save_new_incidents(self, incidents):
        """Save new incidents to database and return list of newly saved incidents"""
        new_incidents = []
        
        for incident in incidents:
            # Check if we've already sent an alert for this incident
            if not Incident.is_already_sent(self.db, incident.incident_hash):
                incident_id = incident.save(self.db)
                if incident_id:  # Successfully saved (was new)
                    new_incidents.append((incident, incident_id))
                    logger.info(f"New incident saved: {incident.location} - {incident.description[:50]}...")
        
        return new_incidents
    
    def run_scrape_cycle(self):
        """Run a complete scrape cycle and return new incidents"""
        logger.info("Starting scrape cycle...")
        
        # Scrape incidents from website
        incidents = self.scrape_incidents()
        
        if not incidents:
            logger.info("No relevant incidents found")
            return []
        
        # Save new incidents to database
        new_incidents = self.save_new_incidents(incidents)
        
        if new_incidents:
            logger.info(f"Found {len(new_incidents)} new incidents to alert on")
        else:
            logger.info("No new incidents to alert on")
        
        return new_incidents

def test_scraper():
    """Test function to run scraper manually"""
    scraper = TranStarScraper()
    new_incidents = scraper.run_scrape_cycle()
    
    print(f"\nFound {len(new_incidents)} new incidents:")
    for incident, incident_id in new_incidents:
        print(f"ID: {incident_id}")
        print(f"Location: {incident.location}")
        print(f"Description: {incident.description}")
        print(f"Time: {incident.incident_time}")
        print(f"Severity: {incident.severity}")
        print("-" * 50)

if __name__ == "__main__":
    test_scraper()
