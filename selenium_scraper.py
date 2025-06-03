import logging
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from models import Incident, Database
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SeleniumTranStarScraper:
    def __init__(self):
        self.url = 'https://traffic.houstontranstar.org/roadclosures/'
        self.db = Database()
        self.driver = None
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            return False
    
    def is_relevant_incident(self, location, description):
        """Check if incident involves heavy trucks or hazmat spills"""
        text = f"{location} {description}".lower()
        
        # First check if this is a street incident (exclude these unless it's a truck)
        if self.is_street_incident(text) and 'truck' not in text:
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
        has_truck = any(keyword in text for keyword in truck_keywords)
        
        # Check for spill incidents (any vehicle type)
        has_spill = any(keyword in text for keyword in spill_keywords)
        
        # Additional patterns for truck incidents
        truck_patterns = [
            r'\b(?:18|eighteen)[\s-]*wheel\w*\b',
            r'\btruck\s+(?:accident|crash|stall|breakdown|rollover)\b',
            r'\b(?:accident|crash)\s+.*\btruck\b',
            r'\bcommercial\s+vehicle\s+(?:accident|crash|stall)\b',
            r'\bheavy\s+truck\b'
        ]
        
        has_pattern = any(re.search(pattern, text) for pattern in truck_patterns)
        
        # Check if this is a stall incident
        is_stall = 'stall' in text or 'breakdown' in text
        
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
            if re.search(pattern, text):
                return False
        
        return True
    
    def scrape_incidents(self):
        """Scrape incidents using Selenium"""
        if not self.setup_driver():
            return []
        
        incidents = []
        
        try:
            logger.info(f"Loading TranStar website: {self.url}")
            self.driver.get(self.url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit more for dynamic content
            time.sleep(5)
            
            # Try to find and click the "Stalls" tab first since that's where the incident was
            try:
                stalls_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Stalls')]"))
                )
                stalls_tab.click()
                logger.info("Clicked on Stalls tab")
                time.sleep(3)  # Wait for content to load
                
                # Scrape stalls table
                stall_incidents = self.scrape_table_section("Stalls")
                incidents.extend(stall_incidents)
                
            except TimeoutException:
                logger.warning("Could not find or click Stalls tab")
            
            # Also try Freeway Incidents tab
            try:
                freeway_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Freeway Incidents')]"))
                )
                freeway_tab.click()
                logger.info("Clicked on Freeway Incidents tab")
                time.sleep(3)
                
                # Scrape freeway incidents table
                freeway_incidents = self.scrape_table_section("Freeway Incidents")
                incidents.extend(freeway_incidents)
                
            except TimeoutException:
                logger.warning("Could not find or click Freeway Incidents tab")
            
            # Try to scrape any visible tables
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            logger.info(f"Found {len(tables)} tables on page")
            
            for table_idx, table in enumerate(tables):
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    logger.info(f"Table {table_idx + 1}: {len(rows)} rows")
                    
                    for row_idx, row in enumerate(rows):
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 3:  # Need at least location, description, status
                                
                                cell_texts = [cell.text.strip() for cell in cells]
                                
                                # Skip header rows
                                if any(header in cell_texts[0].lower() for header in ['location', 'description', 'status']):
                                    continue
                                
                                location = cell_texts[0]
                                description = cell_texts[1] if len(cell_texts) > 1 else "Incident reported"
                                status = cell_texts[2] if len(cell_texts) > 2 else ""
                                
                                # Log potential incidents for debugging
                                full_text = f"{location} | {description} | {status}"
                                if any(keyword in full_text.lower() for keyword in 
                                       ['ih-69', 'eastex', 'fm-1960', 'heavy truck', 'stall', 'truck']):
                                    logger.info(f"🔍 Potential target incident: {full_text}")
                                
                                if location and self.is_relevant_incident(location, description):
                                    incident = self.create_incident(location, description, status)
                                    if incident:
                                        incidents.append(incident)
                                        logger.info(f"✅ Incident found: {incident.location}")
                        
                        except Exception as e:
                            logger.debug(f"Error processing row {row_idx}: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error processing table {table_idx}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
        
        return incidents
    
    def scrape_table_section(self, section_name):
        """Scrape a specific table section"""
        incidents = []
        
        try:
            # Look for tables in the current view
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 3:
                            
                            cell_texts = [cell.text.strip() for cell in cells]
                            
                            # Skip header rows
                            if any(header in cell_texts[0].lower() for header in ['location', 'description', 'status']):
                                continue
                            
                            location = cell_texts[0]
                            description = cell_texts[1] if len(cell_texts) > 1 else "Incident reported"
                            status = cell_texts[2] if len(cell_texts) > 2 else ""
                            
                            # Log all incidents in this section for debugging
                            full_text = f"{location} | {description} | {status}"
                            logger.info(f"📋 {section_name} incident: {full_text}")
                            
                            if location and self.is_relevant_incident(location, description):
                                incident = self.create_incident(location, description, status)
                                if incident:
                                    incidents.append(incident)
                
                except Exception as e:
                    logger.error(f"Error processing table in {section_name}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping {section_name} section: {e}")
        
        return incidents
    
    def create_incident(self, location, description, status):
        """Create incident object from scraped data"""
        try:
            # Clean and format location
            location = self.clean_location(location)
            
            # Clean description
            description = self.clean_description(description)
            
            # Extract time from status
            incident_time = self.extract_time_from_status(status)
            
            # Calculate severity
            severity = self.calculate_severity(f"{location} {description}")
            
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
            logger.error(f"Error creating incident: {e}")
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
        logger.info("Starting Selenium scrape cycle...")
        
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

def test_selenium_scraper():
    """Test the Selenium scraper"""
    scraper = SeleniumTranStarScraper()
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
    test_selenium_scraper()
