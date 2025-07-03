import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://earthquake.phivolcs.dost.gov.ph/"
MONTHLY_URL_PATTERN = "https://earthquake.phivolcs.dost.gov.ph/EQLatest-Monthly/{year}/{year}_{month}.html"

def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.strip())

def parse_location(location_text: str) -> Dict[str, str]:
    location_text = clean_text(location_text)
    
    pattern = r'(\d+)\s*km\s+([NS])\s*(\d+)°?\s*([EW])\s+of\s+(.+?)(?:\s*\(([^)]+)\))?$'
    match = re.search(pattern, location_text)
    
    if match:
        distance = match.group(1)
        ns_direction = match.group(2)
        degree = match.group(3)
        ew_direction = match.group(4)
        place = match.group(5).strip()
        province = match.group(6).strip() if match.group(6) else ""
        
        return {
            "raw_location": location_text,
            "distance_km": distance,
            "direction": f"{ns_direction} {degree}° {ew_direction}",
            "place_name": place,
            "province": province,
            "full_location": f"{place}, {province}" if province else place
        }
    else:
        return {
            "raw_location": location_text,
            "distance_km": "",
            "direction": "",
            "place_name": location_text,
            "province": "",
            "full_location": location_text
        }

def get_browser_headers() -> Dict[str, str]:
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

def get_html_content(source: str) -> str:
    if source.startswith('http'):
        print(f"Fetching data from: {source}")
        headers = get_browser_headers()
        
        try:
            response = requests.get(
                source, 
                headers=headers, 
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            response.raise_for_status()
            print("[OK] Successfully fetched data")
            return response.text
            
        except requests.exceptions.SSLError as e:
            print(f"[WARNING] SSL Error: {e}")
            print("[RETRY] Retrying with SSL verification disabled...")
            response = requests.get(
                source, 
                headers=headers, 
                timeout=30,
                verify=False,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            raise
            
    else:
        print(f"Reading local file: {source}")
        with open(source, 'r', encoding='utf-8') as file:
            return file.read()

def extract_data_period(soup: BeautifulSoup) -> str:
    period_elements = soup.find_all('td', string=True)
    for element in period_elements:
        text = clean_text(element.get_text())
        if re.match(r'^[A-Z]+ \d{4}$', text):
            return text
    
    period_elements = soup.find_all('strong', string=True)
    for element in period_elements:
        text = clean_text(element.get_text())
        if re.match(r'^[A-Z]+ \d{4}$', text):
            return text
    
    date_links = soup.find_all('a')
    for link in date_links:
        text = clean_text(link.get_text())
        if re.search(r'\d{1,2} [A-Za-z]+ \d{4}', text):
            match = re.search(r'(\d{1,2}) ([A-Za-z]+) (\d{4})', text)
            if match:
                month = match.group(2)
                year = match.group(3)
                return f"{month.upper()} {year}"
    
    return "Unknown Period"

def get_available_years_months(soup: BeautifulSoup) -> Dict[str, List[str]]:
    available_data = {}
    
    year_cells = soup.find_all('td', string=True)
    current_year = None
    
    for cell in year_cells:
        text = clean_text(cell.get_text())
        if re.match(r'^\d{4}$', text):
            current_year = text
            available_data[current_year] = []
    
    month_links = soup.find_all('a', href=True)
    for link in month_links:
        href = link.get('href', '')
        if '/EQLatest-Monthly/' in href:
            match = re.search(r'/(\d{4})/\d{4}_([A-Za-z]+)\.html', href)
            if match:
                year = match.group(1)
                month = match.group(2)
                if year not in available_data:
                    available_data[year] = []
                if month not in available_data[year]:
                    available_data[year].append(month)
    
    return available_data

def parse_earthquake_data(source: str) -> Dict[str, Any]:
    content = get_html_content(source)
    soup = BeautifulSoup(content, 'html.parser')
    
    data_period = extract_data_period(soup)
    print(f"Data period detected: {data_period}")
    
    earthquake_rows = []
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) == 6:
            first_cell = cells[0]
            if first_cell.find('a') and 'auto-style91' in first_cell.get('class', []):
                earthquake_rows.append(row)
    
    earthquakes = []
    
    for row in earthquake_rows:
        cells = row.find_all('td')
        if len(cells) >= 6:
            date_cell = cells[0]
            date_link = date_cell.find('a')
            date_time = clean_text(date_link.get_text()) if date_link else ""
            
            latitude = clean_text(cells[1].get_text())
            longitude = clean_text(cells[2].get_text())
            depth = clean_text(cells[3].get_text())
            magnitude = clean_text(cells[4].get_text())
            
            location_text = clean_text(cells[5].get_text())
            location_data = parse_location(location_text)
            
            earthquake = {
                "date_time": date_time,
                "latitude": latitude,
                "longitude": longitude,
                "coordinates_string": f"{latitude}, {longitude}",
                "depth_km": depth,
                "magnitude": magnitude,
                "raw_location": location_data["raw_location"],
                "distance_km": location_data["distance_km"],
                "direction": location_data["direction"],
                "place_name": location_data["place_name"],
                "province": location_data["province"],
                "full_location": location_data["full_location"],
                "location_with_coordinates": f"{location_data['full_location']} ({latitude}, {longitude})"
            }
            
            earthquakes.append(earthquake)
    
    data = {
        "metadata": {
            "source": "PHIVOLCS - Philippine Institute of Volcanology and Seismology",
            "source_url": source if source.startswith('http') else "Local file",
            "total_earthquakes": len(earthquakes),
            "data_period": data_period,
            "extracted_on": datetime.now().isoformat(),
            "columns": [
                "date_time",
                "latitude",
                "longitude",
                "coordinates_string",
                "depth_km",
                "magnitude",
                "raw_location",
                "distance_km",
                "direction",
                "place_name",
                "province",
                "full_location",
                "location_with_coordinates"
            ]
        },
        "earthquakes": earthquakes
    }
    
    return data

def show_available_data() -> Dict[str, List[str]]:
    print("Fetching available years and months...")
    try:
        content = get_html_content(BASE_URL)
        soup = BeautifulSoup(content, 'html.parser')
        available_data = get_available_years_months(soup)
        
        print("\nAvailable earthquake data:")
        print("=" * 50)
        
        for year in sorted(available_data.keys(), reverse=True):
            if available_data[year]:
                months_str = ", ".join(available_data[year])
                print(f"{year}: {months_str}")
            else:
                print(f"{year}: No months found")
        
        return available_data
    except Exception as e:
        print(f"Error fetching available data: {e}")
        return {}

def get_user_selection(available_data: Dict[str, List[str]]) -> Optional[Tuple[str, str]]:
    if not available_data:
        return None
    
    print("\n" + "=" * 50)
    print("SELECT YEAR AND MONTH")
    print("=" * 50)
    
    years = sorted(available_data.keys(), reverse=True)
    print("Available years:")
    for i, year in enumerate(years, 1):
        print(f"{i}. {year}")
    
    try:
        year_choice = input(f"\nSelect year (1-{len(years)}) or press Enter for latest: ").strip()
        
        if not year_choice:
            selected_year = years[0]
        else:
            year_idx = int(year_choice) - 1
            if 0 <= year_idx < len(years):
                selected_year = years[year_idx]
            else:
                print("Invalid year selection")
                return None
        
        available_months = available_data[selected_year]
        if not available_months:
            print(f"No months available for {selected_year}")
            return None
        
        print(f"\nAvailable months for {selected_year}:")
        for i, month in enumerate(available_months, 1):
            print(f"{i}. {month}")
        
        month_choice = input(f"\nSelect month (1-{len(available_months)}) or press Enter for latest: ").strip()
        
        if not month_choice:
            selected_month = available_months[0]
        else:
            month_idx = int(month_choice) - 1
            if 0 <= month_idx < len(available_months):
                selected_month = available_months[month_idx]
            else:
                print("Invalid month selection")
                return None
        
        return selected_year, selected_month
        
    except (ValueError, KeyboardInterrupt):
        print("\nOperation cancelled")
        return None

def build_url(year: str, month: str) -> str:
    return MONTHLY_URL_PATTERN.format(year=year, month=month)

def main():
    print("PHIVOLCS Earthquake Data Parser")
    print("=" * 50)
    
    print("\nOptions:")
    print("1. Parse latest data (current page)")
    print("2. Select specific year/month")
    
    choice = input("\nSelect option (1-2): ").strip()
    
    if choice == "1":
        source = BASE_URL
        output_file = "earthquake_data_latest.json"
        
    elif choice == "2":
        available_data = show_available_data()
        selection = get_user_selection(available_data)
        
        if not selection:
            print("No valid selection made. Exiting.")
            return
        
        year, month = selection
        source = build_url(year, month)
        output_file = f"earthquake_data_{year}_{month}.json"
        
    # elif choice == "3":
    #     filename = input("Enter HTML filename: ").strip()
    #     if not filename:
    #         filename = "index.html"
    #     source = filename
    #     output_file = "earthquake_data_local.json"
        
    else:
        print("Invalid option")
        return
    
    try:
        print(f"\nParsing earthquake data from: {source}")
        earthquake_data = parse_earthquake_data(source)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(earthquake_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SUCCESS] Successfully parsed {earthquake_data['metadata']['total_earthquakes']} earthquake records")
        print(f"[SUCCESS] Data saved to {output_file}")
        print(f"[SUCCESS] Data period: {earthquake_data['metadata']['data_period']}")
        print(f"[SUCCESS] Source: {earthquake_data['metadata']['source_url']}")
        
        if earthquake_data['earthquakes']:
            print(f"\n[DATA] Sample earthquake data:")
            for i, eq in enumerate(earthquake_data['earthquakes'][:3]):
                print(f"{i+1}. {eq['date_time']} | Mag: {eq['magnitude']} | {eq['full_location']} | Coords: {eq['coordinates_string']}")
        
    except requests.RequestException as e:
        print(f"[ERROR] Network error: {e}")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {source}")
    except Exception as e:
        print(f"[ERROR] Error parsing data: {str(e)}")

if __name__ == "__main__":
    main() 