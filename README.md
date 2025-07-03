# PHIVOLCS Earthquake Data Parser

A Python tool to scrape and convert PHIVOLCS (Philippine Institute of Volcanology and Seismology) earthquake data from HTML to structured JSON format.

## Features

- Web scraping of live earthquake data from PHIVOLCS website
- Historical data access from 2018-2025
- Dynamic period detection from HTML
- Interactive year/month selection
- Structured JSON output with location details and coordinates

## Installation

```bash
pip install -r requirements.txt
python earthquake_parser.py
```

## Usage Options

**Option 1: Latest Data**
- Fetches current earthquake data from main PHIVOLCS page
- Output: `earthquake_data_latest.json`

**Option 2: Historical Data**
- Browse and select specific year/month combinations (2018-2025)
- Interactive selection from available data
- Output: `earthquake_data_{YEAR}_{MONTH}.json`

## JSON Output Structure

The parser outputs structured JSON with metadata and earthquake records:

```json
{
  "metadata": {
    "source": "PHIVOLCS - Philippine Institute of Volcanology and Seismology",
    "source_url": "https://earthquake.phivolcs.dost.gov.ph/",
    "total_earthquakes": 150,
    "data_period": "JULY 2025",
    "extracted_on": "2025-01-03T10:30:00"
  },
  "earthquakes": [
    {
      "date_time": "03 July 2025 - 01:27 PM",
      "latitude": "13.62",
      "longitude": "120.70",
      "coordinates_string": "13.62, 120.70",
      "depth_km": "013",
      "magnitude": "1.7",
      "raw_location": "020 km N 07° W of Abra De Ilog (Occidental Mindoro)",
      "distance_km": "020",
      "direction": "N 07° W",
      "place_name": "Abra De Ilog",
      "province": "Occidental Mindoro",
      "full_location": "Abra De Ilog, Occidental Mindoro",
      "location_with_coordinates": "Abra De Ilog, Occidental Mindoro (13.62, 120.70)"
    }
  ]
}
```

## Dependencies

- requests (web scraping)
- beautifulsoup4 (HTML parsing)
- lxml (XML/HTML parser)
- urllib3 (SSL warning suppression)

## Notes

- All times are in Philippine Standard Time (UTC+8)
- Data is sourced directly from PHIVOLCS official website
- Historical data availability varies by year and month
- Respects rate limiting for responsible web scraping 