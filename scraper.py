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
        
        # First check if this is a street incident (exclude these)
        if self.is_street_incident(text):
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
    
    def is_street_incident(self, text):
        """Check if this is a street incident that should be excluded"""
        text_lower = text.lower()
        
        # Check if incident is on a major highway/freeway (INCLUDE these)
        major_roads = [
            # Interstates
            r'\bi-\d+\b', r'\binterstate\s+\d+\b',
            
            # US Highways
            r'\bus-?\d+\b', r'\bus\s+highway\s+\d+\b',
            
            # State Highways
            r'\bhighway\s+\d+\b', r'\bhwy\s+\d+\b', r'\bstate\s+highway\s+\d+\b',
            
            # Houston Major Roads
            r'\bbeltway\s+8\b', r'\bloop\s+610\b', r'\bloop\s+\d+\b',
            
            # Toll Roads
            r'\btoll\s+road\b', r'\btollway\b',
            r'\bhardy\s+toll\b', r'\bwestpark\s+toll\b', r'\bsam\s+houston\s+toll\b',
            
            # Major Freeways (by name)
            r'\bkaty\s+freeway\b', r'\bkaty\s+fwy\b',
            r'\bgulf\s+freeway\b', r'\bgulf\s+fwy\b',
            r'\bsouthwest\s+freeway\b', r'\bsouthwest\s+fwy\b',
            r'\bnorthwest\s+freeway\b', r'\bnorthwest\s+fwy\b',
            r'\beast\s+freeway\b', r'\beast\s+fwy\b',
            r'\beastex\s+freeway\b', r'\beastex\s+fwy\b',
            r'\bnorth\s+freeway\b', r'\bnorth\s+fwy\b',
            r'\bsouth\s+freeway\b', r'\bsouth\s+fwy\b',
            
            # General freeway pattern
            r'\b\w+\s+freeway\b', r'\b\w+\s+fwy\b',
        ]
        
        # If it's on a major road, it's NOT a street incident
        for pattern in major_roads:
            if re.search(pattern, text_lower):
                return False
        
        # Check for street incident patterns (EXCLUDE these)
        street_patterns = [
            # Common street types
            r'\b\w+\s+street\b', r'\b\w+\s+st\b',
            r'\b\w+\s+avenue\b', r'\b\w+\s+ave\b',
            r'\b\w+\s+drive\b', r'\b\w+\s+dr\b',
            r'\b\w+\s+lane\b', r'\b\w+\s+ln\b',
            r'\b\w+\s+court\b', r'\b\w+\s+ct\b',
            r'\b\w+\s+circle\b', r'\b\w+\s+cir\b',
            r'\b\w+\s+place\b', r'\b\w+\s+pl\b',
            r'\b\w+\s+way\b',
            
            # Specific Houston streets that are NOT highways
            r'\bmain\s+street\b', r'\bmain\s+st\b',
            r'\bwestheimer\s+road\b', r'\bwestheimer\s+rd\b',
            r'\bmemorial\s+drive\b', r'\bmemorial\s+dr\b',
            r'\bkirby\s+drive\b', r'\bkirby\s+dr\b',
            r'\bpost\s+oak\b', r'\bpost\s+oak\s+blvd\b',
            r'\bsage\s+road\b', r'\bsage\s+rd\b',
            r'\bbissonnet\b', r'\brichmond\s+ave\b',
            r'\bhillcroft\b', r'\bgessner\b',
            r'\bfondren\b', r'\bsharpstown\b',
            
            # Residential/local indicators
            r'\bsubdivision\b', r'\bneighborhood\b',
            r'\bresidential\b', r'\blocal\s+street\b',
            r'\bparking\s+lot\b', r'\bshopping\s+center\b',
        ]
        
        # If it matches street patterns, it's a street incident
        for pattern in street_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Additional check: if location contains common street words without highway indicators
        street_words = ['street', 'avenue', 'drive', 'lane', 'court', 'circle', 'place']
        highway_words = ['freeway', 'highway', 'interstate', 'beltway', 'loop', 'toll']
        
        has_street_words = any(word in text_lower for word in street_words)
        has_highway_words = any(word in text_lower for word in highway_words)
        
        # If it has street words but no highway words, likely a street incident
        if has_street_words and not has_highway_words:
            return True
        
        return False
    
    def is_highway_location(self, location):
        """Check if a location is on a major highway/freeway"""
        if not location:
            return False
            
        location_lower = location.lower()
        
        # Major highway patterns
        highway_patterns = [
            r'\bi-\d+\b', r'\bus-?\d+\b', r'\bhwy\s+\d+\b',
            r'\bbeltway\b', r'\bloop\b', r'\btoll\b', r'\btollway\b',
            r'\bfreeway\b', r'\bfwy\b'
        ]
        
        return any(re.search(pattern, location_lower) for pattern in highway_patterns)
    
    def extract_location(self, text):
        """Extract location from incident text and format as Street1 @ Street2"""
        # First, look for existing @ symbol (preserve TranStar formatting)
        if '@' in text:
            # Find the @ symbol and extract surrounding context
            at_index = text.find('@')
            # Get text before and after @
            before_at = text[:at_index].strip()
            after_at = text[at_index+1:].strip()
            
            # Extract the street names around @
            before_words = before_at.split()[-3:]  # Last 3 words before @
            after_words = after_at.split()[:3]     # First 3 words after @
            
            street1 = ' '.join(before_words).strip()
            street2 = ' '.join(after_words).strip()
            
            if street1 and street2:
                return f"{self.standardize_street_name(street1)} @ {self.standardize_street_name(street2)}"
        
        # Enhanced Houston highway and road patterns with cross streets
        patterns = [
            # Interstate patterns with cross streets
            r'(I-\d+[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            r'(Interstate\s+\d+[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            
            # US Highway patterns
            r'(US-?\d+[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            r'(Highway\s+\d+[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            
            # Houston specific roads
            r'(Beltway\s+8[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            r'(Loop\s+\d+[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            
            # Toll roads (Hardy Toll Road, Westpark Tollway, etc.)
            r'([\w\s]+Toll\s+Road[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            r'([\w\s]+Tollway[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            
            # Freeway patterns
            r'([\w\s]+Freeway[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
            
            # General street patterns
            r'([\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd)[NSEW]?)\s+(?:at|near|and|@)\s+([\w\s\-]+?)(?:\s|$|,|\.|;)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                street1 = match.group(1).strip()
                street2 = match.group(2).strip()
                
                # Clean up the cross street (remove extra words)
                street2 = self.clean_cross_street(street2)
                
                if street1 and street2:
                    return f"{self.standardize_street_name(street1)} @ {self.standardize_street_name(street2)}"
        
        # Fallback - try to extract at least the main road
        main_road_patterns = [
            r'(I-\d+[NSEW]?)',
            r'(US-?\d+[NSEW]?)',
            r'(Highway\s+\d+[NSEW]?)',
            r'(Beltway\s+8[NSEW]?)',
            r'(Loop\s+\d+[NSEW]?)',
            r'([\w\s]+Toll\s+Road[NSEW]?)',
            r'([\w\s]+Tollway[NSEW]?)',
            r'([\w\s]+Freeway[NSEW]?)',
        ]
        
        for pattern in main_road_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                road = self.standardize_street_name(match.group(1).strip())
                return f"{road} @ [Cross Street]"
        
        # Final fallback - look for any location-like text
        location_words = ['at', 'near', 'on', 'between']
        for word in location_words:
            if word in text.lower():
                parts = text.split(word, 1)
                if len(parts) > 1:
                    location = parts[1].strip()[:50]
                    if location:
                        return self.standardize_street_name(location)
        
        return "Houston Area"
    
    def standardize_street_name(self, street):
        """Standardize street name formatting"""
        if not street:
            return street
            
        street = street.strip()
        
        # Highway standardization
        street = re.sub(r'\bInterstate\s+(\d+)', r'I-\1', street, flags=re.IGNORECASE)
        street = re.sub(r'\bUS\s+(\d+)', r'US-\1', street, flags=re.IGNORECASE)
        street = re.sub(r'\bHighway\s+(\d+)', r'Hwy \1', street, flags=re.IGNORECASE)
        
        # Street type abbreviations
        replacements = {
            r'\bFreeway\b': 'Fwy',
            r'\bBoulevard\b': 'Blvd',
            r'\bAvenue\b': 'Ave',
            r'\bStreet\b': 'St',
            r'\bRoad\b': 'Rd',
            r'\bDrive\b': 'Dr',
            r'\bLane\b': 'Ln',
            r'\bParkway\b': 'Pkwy',
        }
        
        for pattern, replacement in replacements.items():
            street = re.sub(pattern, replacement, street, flags=re.IGNORECASE)
        
        # Handle directional indicators
        street = re.sub(r'\b(North|South|East|West)bound\b', lambda m: m.group(1)[0] + 'B', street, flags=re.IGNORECASE)
        street = re.sub(r'\b(North|South|East|West)\b', lambda m: m.group(1)[0], street, flags=re.IGNORECASE)
        
        return street
    
    def clean_cross_street(self, cross_street):
        """Clean up cross street name by removing extra words"""
        if not cross_street:
            return cross_street
            
        # Remove common extra words that might be captured
        words_to_remove = [
            'accident', 'crash', 'incident', 'blocked', 'blocking', 'closed',
            'stalled', 'breakdown', 'collision', 'reported', 'heavy', 'truck',
            'semi', 'vehicle', 'traffic', 'lanes', 'lane'
        ]
        
        words = cross_street.split()
        cleaned_words = []
        
        for word in words:
            if word.lower() not in words_to_remove and len(word) > 1:
                cleaned_words.append(word)
                # Stop at first 2-3 meaningful words for cross street
                if len(cleaned_words) >= 3:
                    break
        
        return ' '.join(cleaned_words) if cleaned_words else cross_street
    
    def extract_time(self, text):
        """Extract time from incident text and convert to 12-hour format"""
        time_pattern = r'\d{1,2}:\d{2}(?:\s*[APap][Mm])?'
        match = re.search(time_pattern, text)
        
        if match:
            time_str = match.group()
            return self.convert_to_12_hour(time_str)
        else:
            # Default to current time in 12-hour format
            return datetime.now().strftime("%I:%M %p")
    
    def convert_to_12_hour(self, time_str):
        """Convert time string to 12-hour format with AM/PM"""
        try:
            # If already has AM/PM, just clean it up
            if re.search(r'[APap][Mm]', time_str):
                # Clean up the AM/PM format
                time_str = re.sub(r'\s*([APap])[Mm]', r' \1M', time_str)
                return time_str.upper()
            
            # Parse 24-hour format and convert to 12-hour
            time_parts = time_str.split(':')
            if len(time_parts) == 2:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Convert to 12-hour format
                if hour == 0:
                    return f"12:{minute:02d} AM"
                elif hour < 12:
                    return f"{hour}:{minute:02d} AM"
                elif hour == 12:
                    return f"12:{minute:02d} PM"
                else:
                    return f"{hour-12}:{minute:02d} PM"
            
        except (ValueError, IndexError):
            pass
        
        # Fallback to current time if parsing fails
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
        
        # Multiple vehicles
        if any(keyword in description_lower for keyword in ['multiple', 'multi-vehicle', 'pile-up']):
            severity += 1
        
        # Lane blockages
        if any(keyword in description_lower for keyword in ['blocked', 'blocking', 'closed']):
            severity += 1
        
        return min(severity, 5)  # Cap at 5
    
    def scrape_incidents(self):
        """Scrape incidents from TranStar website with enhanced detection"""
        try:
            logger.info(f"Scraping incidents from {self.url}")
            
            response = self.session.get(self.url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            incidents = []
            
            # Method 1: Look for incident data in tables (original method)
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables to analyze")
            
            for table_idx, table in enumerate(tables):
                rows = table.find_all('tr')
                logger.info(f"Table {table_idx + 1}: {len(rows)} rows")
                
                for row_idx, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:  # Lowered threshold to catch more data
                        
                        # Extract text from all cells
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        full_text = " | ".join(cell_texts)
                        
                        # Log for debugging
                        if any(keyword in full_text.lower() for keyword in ['truck', 'semi', 'accident', 'crash', 'toll']):
                            logger.info(f"Potential incident found in table {table_idx + 1}, row {row_idx + 1}: {full_text[:100]}...")
                        
                        # Check if this is a relevant incident
                        if self.is_relevant_incident(full_text):
                            incident = self.create_incident_from_text(cell_texts, full_text)
                            if incident:
                                incidents.append(incident)
                                logger.info(f"✅ Relevant incident detected: {incident.location}")
            
            # Method 2: Look for incident data in divs and spans
            incident_elements = soup.find_all(['div', 'span', 'p', 'li'], 
                                            class_=re.compile(r'incident|alert|closure|traffic|road|event', re.I))
            logger.info(f"Found {len(incident_elements)} potential incident elements")
            
            for element in incident_elements:
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Skip very short text
                    
                    # Log potential incidents
                    if any(keyword in text.lower() for keyword in ['truck', 'semi', 'accident', 'crash', 'toll']):
                        logger.info(f"Potential incident in element: {text[:100]}...")
                    
                    if self.is_relevant_incident(text):
                        incident = self.create_incident_from_text([text], text)
                        if incident:
                            incidents.append(incident)
                            logger.info(f"✅ Relevant incident detected from element: {incident.location}")
            
            # Method 3: Look for any text containing truck/accident keywords
            all_text_elements = soup.find_all(text=True)
            combined_text = " ".join([t.strip() for t in all_text_elements if t.strip()])
            
            # Split into potential incident chunks
            text_chunks = self.split_into_incident_chunks(combined_text)
            logger.info(f"Analyzing {len(text_chunks)} text chunks for incidents")
            
            for chunk in text_chunks:
                if len(chunk) > 20 and self.is_relevant_incident(chunk):
                    
                    # Log potential incidents
                    if any(keyword in chunk.lower() for keyword in ['truck', 'semi', 'accident', 'crash', 'toll']):
                        logger.info(f"Potential incident in text chunk: {chunk[:100]}...")
                    
                    incident = self.create_incident_from_text([chunk], chunk)
                    if incident:
                        incidents.append(incident)
                        logger.info(f"✅ Relevant incident detected from text: {incident.location}")
            
            # Remove duplicates based on location and description similarity
            unique_incidents = self.remove_duplicate_incidents(incidents)
            
            logger.info(f"Found {len(incidents)} total incidents, {len(unique_incidents)} unique incidents")
            return unique_incidents
            
        except requests.RequestException as e:
            logger.error(f"Error scraping TranStar: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return []
    
    def create_incident_from_text(self, cell_texts, full_text):
        """Create incident object from text data"""
        try:
            # Extract incident details
            location = self.extract_location(cell_texts[0] if cell_texts and cell_texts[0] else full_text)
            description = cell_texts[1] if len(cell_texts) > 1 else full_text
            incident_time = self.extract_time(cell_texts[2] if len(cell_texts) > 2 else full_text)
            severity = self.calculate_severity(description)
            
            # Clean up description
            description = description[:200]  # Limit length
            if not description or len(description.strip()) < 5:
                description = "Heavy truck incident reported"
            
            # Skip if location is too generic
            if location in ["Houston Area", "[Cross Street]"]:
                return None
            
            incident = Incident(
                location=location,
                description=description,
                incident_time=incident_time,
                severity=severity
            )
            
            return incident
            
        except Exception as e:
            logger.error(f"Error creating incident from text: {e}")
            return None
    
    def split_into_incident_chunks(self, text):
        """Split large text into potential incident chunks"""
        # Split on common separators
        separators = ['\n', '|', ';', '.', '  ']  # Double space
        chunks = [text]
        
        for separator in separators:
            new_chunks = []
            for chunk in chunks:
                new_chunks.extend(chunk.split(separator))
            chunks = new_chunks
        
        # Filter chunks that might contain incidents
        incident_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if (len(chunk) > 20 and 
                any(keyword in chunk.lower() for keyword in 
                    ['truck', 'semi', 'accident', 'crash', 'i-', 'us-', 'highway', 'toll', 'freeway'])):
                incident_chunks.append(chunk)
        
        return incident_chunks[:50]  # Limit to prevent too many chunks
    
    def remove_duplicate_incidents(self, incidents):
        """Remove duplicate incidents based on location and description similarity"""
        unique_incidents = []
        
        for incident in incidents:
            is_duplicate = False
            
            for existing in unique_incidents:
                # Check if locations are similar
                location_similar = (incident.location.lower() == existing.location.lower() or
                                  incident.location.lower() in existing.location.lower() or
                                  existing.location.lower() in incident.location.lower())
                
                # Check if descriptions are similar
                desc_words1 = set(incident.description.lower().split())
                desc_words2 = set(existing.description.lower().split())
                common_words = desc_words1.intersection(desc_words2)
                desc_similar = len(common_words) > 3  # At least 4 common words
                
                if location_similar and desc_similar:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_incidents.append(incident)
        
        return unique_incidents
    
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
