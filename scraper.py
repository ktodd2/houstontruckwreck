import requests
from bs4 import BeautifulSoup
import re
import logging
import json
from datetime import datetime
from models import Incident, Database
from config import Config
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranStarScraper:
    def __init__(self):
        self.base_url = 'https://traffic.houstontranstar.org'
        self.api_endpoints = [
            '/api/incidents/freeway',
            '/api/incidents/stalls', 
            '/api/incidents/street',
            '/api/incidents/closures'
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://traffic.houstontranstar.org/roadclosures/',
            'Origin': 'https://traffic.houstontranstar.org'
        })
        self.db = Database()
    
    def is_relevant_incident(self, incident_data):
        """Check if incident involves heavy trucks or hazmat spills"""
        # Handle both dict and string inputs
        if isinstance(incident_data, dict):
            text = f"{incident_data.get('location', '')} {incident_data.get('description', '')} {incident_data.get('type', '')}"
        else:
            text = str(incident_data)
        
        text_lower = text.lower()
        
        # First check if this is a street incident (exclude these unless it's a truck)
        if self.is_street_incident(text) and 'truck' not in text_lower:
            logger.info(f"🚫 Excluding street incident: {text[:100]}...")
            return False
        
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
            r'\bcommercial\s+vehicle\s+(?:accident|crash|stall)\b',
            r'\bheavy\s+truck\b'
        ]
        
        has_pattern = any(re.search(pattern, text_lower) for pattern in truck_patterns)
        
        # Check if this is a stall incident
        is_stall = 'stall' in text_lower or 'breakdown' in text_lower
        
        # If stalls are disabled and this is a stall, exclude it
        from models import Settings
        if is_stall and not Settings.get_include_stalls(self.db):
            logger.info(f"🚫 Excluding stall (stalls disabled): {text[:100]}...")
            return False
        
        result = has_truck or has_spill or has_pattern
        if result:
            logger.info(f"✅ Relevant incident found: {text[:100]}...")
        
        return result
    
    def is_street_incident(self, text):
        """Check if this is a street incident that should be excluded"""
        text_lower = text.lower()
        
        # Check if incident is on a major highway/freeway (INCLUDE these)
        major_roads = [
            r'\bi-\d+\b', r'\bih-\d+\b', r'\binterstate\s+\d+\b',
            r'\bus-?\d+\b', r'\bus\s+highway\s+\d+\b',
            r'\bhighway\s+\d+\b', r'\bhwy\s+\d+\b', r'\bstate\s+highway\s+\d+\b',
            r'\bbeltway\s+8\b', r'\bloop\s+610\b', r'\bloop\s+\d+\b',
            r'\btoll\s+road\b', r'\btollway\b',
            r'\bhardy\s+toll\b', r'\bwestpark\s+toll\b', r'\bsam\s+houston\s+toll\b',
            r'\beastex\s+freeway\b', r'\beastex\s+fwy\b', r'\beastex\b',
            r'\b\w+\s+freeway\b', r'\b\w+\s+fwy\b',
        ]
        
        # If it's on a major road, it's NOT a street incident
        for pattern in major_roads:
            if re.search(pattern, text_lower):
                return False
        
        return True
    
    def scrape_api_endpoints(self):
        """Try to scrape from API endpoints"""
        incidents = []
        
        for endpoint in self.api_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                logger.info(f"Trying API endpoint: {url}")
                
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"API endpoint {endpoint} returned {len(data) if isinstance(data, list) else 'unknown'} items")
                        
                        if isinstance(data, list):
                            for item in data:
                                if self.is_relevant_incident(item):
                                    incident = self.create_incident_from_api_data(item)
                                    if incident:
                                        incidents.append(incident)
                        elif isinstance(data, dict) and 'incidents' in data:
                            for item in data['incidents']:
                                if self.is_relevant_incident(item):
                                    incident = self.create_incident_from_api_data(item)
                                    if incident:
                                        incidents.append(incident)
                    except json.JSONDecodeError:
                        logger.warning(f"API endpoint {endpoint} returned non-JSON data")
                        continue
                else:
                    logger.warning(f"API endpoint {endpoint} returned status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error accessing API endpoint {endpoint}: {e}")
                continue
        
        return incidents
    
    def scrape_html_fallback(self):
        """Fallback to HTML scraping with improved parsing"""
        try:
            url = 'https://traffic.houstontranstar.org/roadclosures/'
            logger.info(f"Fallback: Scraping HTML from {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            incidents = []
            
            # Look for script tags that might contain incident data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('incident' in script.string.lower() or 'stall' in script.string.lower()):
                    # Try to extract JSON data from script
                    script_content = script.string
                    
                    # Look for JSON-like structures
                    json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', script_content)
                    for match in json_matches:
                        try:
                            data = json.loads(match)
                            if isinstance(data, dict) and any(key in data for key in ['location', 'description', 'type']):
                                if self.is_relevant_incident(data):
                                    incident = self.create_incident_from_api_data(data)
                                    if incident:
                                        incidents.append(incident)
                        except:
                            continue
            
            # Also try the original table parsing method
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables to analyze")
            
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:  # Need at least location, description, status
                        
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        full_text = " | ".join(cell_texts)
                        
                        # Check if this looks like an incident row
                        if any(keyword in full_text.lower() for keyword in 
                               ['stall', 'accident', 'crash', 'truck', 'heavy', 'verified', 'detected']):
                            
                            if self.is_relevant_incident(full_text):
                                incident = self.create_incident_from_html_row(cell_texts)
                                if incident:
                                    incidents.append(incident)
                                    logger.info(f"✅ HTML incident found: {incident.location}")
            
            return incidents
            
        except Exception as e:
            logger.error(f"Error in HTML fallback scraping: {e}")
            return []
    
    def create_incident_from_api_data(self, data):
        """Create incident from API data"""
        try:
            location = data.get('location', '') or data.get('roadway', '') or 'Unknown Location'
            description = data.get('description', '') or data.get('type', '') or 'Incident reported'
            
            # Handle time
            time_str = data.get('time', '') or data.get('reported_time', '') or data.get('updated', '')
            if time_str:
                incident_time = self.parse_time_string(time_str)
            else:
                incident_time = datetime.now().strftime("%I:%M %p")
            
            # Calculate severity
            severity = self.calculate_severity(f"{location} {description}")
            
            # Clean up location and description
            location = self.clean_location(location)
            description = self.clean_description(description)
            
            if not location or location == 'Unknown Location':
                return None
            
            incident = Incident(
                location=location,
                description=description,
                incident_time=incident_time,
                severity=severity
            )
            
            return incident
            
        except Exception as e:
            logger.error(f"Error creating incident from API data: {e}")
            return None
    
    def create_incident_from_html_row(self, cell_texts):
        """Create incident from HTML table row"""
        try:
            if len(cell_texts) < 3:
                return None
            
            # Typical format: [Location, Description, Status/Time, ...]
            location = cell_texts[0]
            description = cell_texts[1] if len(cell_texts) > 1 else "Incident reported"
            status_time = cell_texts[2] if len(cell_texts) > 2 else ""
            
            # Extract time from status
            incident_time = self.extract_time_from_status(status_time)
            
            # Calculate severity
            severity = self.calculate_severity(f"{location} {description}")
            
            # Clean up
            location = self.clean_location(location)
            description = self.clean_description(description)
            
            if not location:
                return None
            
            incident = Incident(
                location=location,
                description=description,
                incident_time=incident_time,
                severity=severity
            )
            
            return incident
            
        except Exception as e:
            logger.error(f"Error creating incident from HTML row: {e}")
            return None
    
    def clean_location(self, location):
        """Clean and standardize location string"""
        if not location:
            return None
        
        location = location.strip()
        
        # Handle common TranStar location formats
        # "IH-69 Eastex Northbound After FM-1960" -> "IH-69 Eastex NB @ FM-1960"
        location = re.sub(r'\b(North|South|East|West)bound\b', lambda m: m.group(1)[0] + 'B', location)
        location = re.sub(r'\bAfter\b', '@', location, flags=re.IGNORECASE)
        location = re.sub(r'\bBefore\b', '@', location, flags=re.IGNORECASE)
        location = re.sub(r'\bAt\b', '@', location, flags=re.IGNORECASE)
        location = re.sub(r'\bNear\b', '@', location, flags=re.IGNORECASE)
        
        # Standardize highway names
        location = re.sub(r'\bIH-(\d+)', r'IH-\1', location)
        location = re.sub(r'\bI-(\d+)', r'IH-\1', location)
        location = re.sub(r'\bUS-(\d+)', r'US-\1', location)
        
        return location
    
    def clean_description(self, description):
        """Clean and standardize description"""
        if not description:
            return "Incident reported"
        
        description = description.strip()
        
        # Limit length
        if len(description) > 200:
            description = description[:200] + "..."
        
        return description
    
    def parse_time_string(self, time_str):
        """Parse various time string formats"""
        if not time_str:
            return datetime.now().strftime("%I:%M %p")
        
        # Handle "Verified at 3:16 PM" format
        time_match = re.search(r'(\d{1,2}:\d{2}\s*[APap][Mm])', time_str)
        if time_match:
            return time_match.group(1).upper()
        
        # Handle 24-hour format
        time_match = re.search(r'(\d{1,2}:\d{2})', time_str)
        if time_match:
            try:
                time_obj = datetime.strptime(time_match.group(1), '%H:%M')
                return time_obj.strftime("%I:%M %p")
            except:
                pass
        
        return datetime.now().strftime("%I:%M %p")
    
    def extract_time_from_status(self, status):
        """Extract time from status string like 'Verified at 3:16 PM'"""
        if not status:
            return datetime.now().strftime("%I:%M %p")
        
        # Look for time patterns
        time_patterns = [
            r'(\d{1,2}:\d{2}\s*[APap][Mm])',
            r'at\s+(\d{1,2}:\d{2}\s*[APap][Mm])',
            r'(\d{1,2}:\d{2})'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, status, re.IGNORECASE)
            if match:
                time_str = match.group(1)
                if re.search(r'[APap][Mm]', time_str):
                    return time_str.upper()
                else:
                    # Convert 24-hour to 12-hour
                    try:
                        time_obj = datetime.strptime(time_str, '%H:%M')
                        return time_obj.strftime("%I:%M %p")
                    except:
                        pass
        
        return datetime.now().strftime("%I:%M %p")
    
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
        
        # Heavy truck incidents get higher priority
        if 'heavy truck' in description_lower:
            severity += 1
        
        # Multiple vehicles
        if any(keyword in description_lower for keyword in ['multiple', 'multi-vehicle', 'pile-up']):
            severity += 1
        
        # Lane blockages
        if any(keyword in description_lower for keyword in ['blocked', 'blocking', 'closed']):
            severity += 1
        
        return min(severity, 5)  # Cap at 5
    
    def scrape_incidents(self):
        """Main scraping method - try API first, then HTML fallback"""
        logger.info("Starting improved incident scraping...")
        
        # Try API endpoints first
        incidents = self.scrape_api_endpoints()
        
        if not incidents:
            logger.info("No incidents from API, trying HTML fallback...")
            incidents = self.scrape_html_fallback()
        
        # Remove duplicates
        unique_incidents = self.remove_duplicate_incidents(incidents)
        
        logger.info(f"Found {len(incidents)} total incidents, {len(unique_incidents)} unique incidents")
        return unique_incidents
    
    def remove_duplicate_incidents(self, incidents):
        """Remove duplicate incidents"""
        unique_incidents = []
        seen_hashes = set()
        
        for incident in incidents:
            if incident.incident_hash not in seen_hashes:
                unique_incidents.append(incident)
                seen_hashes.add(incident.incident_hash)
        
        return unique_incidents
    
    def save_new_incidents(self, incidents):
        """Save new incidents to database"""
        new_incidents = []
        
        for incident in incidents:
            if not Incident.is_already_sent(self.db, incident.incident_hash):
                incident_id = incident.save(self.db)
                if incident_id:
                    new_incidents.append((incident, incident_id))
                    logger.info(f"New incident saved: {incident.location} - {incident.description[:50]}...")
        
        return new_incidents
    
    def run_scrape_cycle(self):
        """Run complete scrape cycle"""
        logger.info("Starting improved scrape cycle...")
        
        incidents = self.scrape_incidents()
        
        if not incidents:
            logger.info("No relevant incidents found")
            return []
        
        new_incidents = self.save_new_incidents(incidents)
        
        if new_incidents:
            logger.info(f"Found {len(new_incidents)} new incidents to alert on")
        else:
            logger.info("No new incidents to alert on")
        
        return new_incidents

def test_scraper():
    """Test the scraper"""
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
