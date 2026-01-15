import json
import folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time
import sys
import re

# Force utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Load data
with open('schools_data.json', 'r', encoding='utf-8') as f:
    schools = json.load(f)

print(f"Loaded {len(schools)} schools.")

# Initialize geocoder
geolocator = Nominatim(user_agent="berlin_school_mapper_1.0", timeout=10)
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

# Create map centered on Berlin
m = folium.Map(location=[52.5200, 13.4050], zoom_start=11)

# Feature Groups for Layers
gymnasium_group = folium.FeatureGroup(name="Gymnasien")
iss_group = folium.FeatureGroup(name="Integrierte Sekundarschulen (ISS)")
other_group = folium.FeatureGroup(name="Andere")

# Helper to add marker
def add_marker(lat, lon, name, popup_html, color, group):
    folium.Marker(
        [lat, lon],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=name,
        icon=folium.Icon(color=color)
    ).add_to(group)

# Randomize order to process a mix of schools early
import random
random.shuffle(schools)

processed_count = 0

try:
    for school in schools:
        name = school.get('name')
        address = school.get('address')
        school_type = school.get('school_type', 'Gymnasium')
        homepage = school.get('homepage')
        url = school.get('url')
        
        # Determine color and group
        color = 'gray'
        target_group = other_group
        
        if 'Gymnasium' in school_type:
            color = 'blue'
            target_group = gymnasium_group
        elif 'ISS' in school_type or 'Sekundarschule' in school_type:
            color = 'red'
            target_group = iss_group
        else:
            color = 'gray'
            target_group = other_group
    
        if address:
            print(f"Geocoding: {name} ({address})...")
            try:
                clean_addr = address
                zip_code = None
                
                # 1. Detect Zip and surrounding
                match = re.search(r'(\d{5})\s+Berlin', clean_addr)
                if match:
                    zip_code = match.group(1)
                    pre_zip = clean_addr[:match.start()]
                    # 2. Cleanup pre_zip
                    # Remove "Stadtplan", "Telefon" etc if scraper missed them
                    for garbage in ["Stadtplan", "Telefon", "Schulleitung"]:
                            pre_zip = re.sub(garbage, '', pre_zip, flags=re.IGNORECASE)
                    
                    # Remove school codes (e.g. 04Y11, 4Y10) 
                    # Regex: 1-2 digits, Letter, 2 digits
                    pre_zip = re.sub(r'\b\d{1,2}[A-Z]\d{2}\b', '', pre_zip)
                    pre_zip = re.sub(r'Gymnasien\s*\(\s*öffentlich\s*\)', '', pre_zip)
                    pre_zip = re.sub(r'Gymnasium', '', pre_zip) 
                    pre_zip = pre_zip.replace("-", "").strip()
                    clean_addr = f"{pre_zip.strip()} {zip_code} Berlin"
                
                clean_addr = " ".join(clean_addr.split())
                
                # Retry logic for Address
                location = None
                for attempt in range(2):
                    try:
                        location = geocode(clean_addr)
                        if location:
                            break
                    except Exception as e:
                        print(f"    (Attempt {attempt+1} failed: {e})")
                        time.sleep(1.5)
                
                if location:
                    print(f"  -> Found: {location.latitude}, {location.longitude} ('{clean_addr}')")
                    print(f"     [Debug] Type: {school_type} -> Color: {color}") 
                    
                    # Build Popup
                    popup_html = f"<b>{name}</b><br><i>{school_type}</i><br>{clean_addr}<br>"
                    if homepage:
                        popup_html += f"<a href='{homepage}' target='_blank'>Homepage</a> | "
                    popup_html += f"<a href='{url}' target='_blank'>Schulprofil</a>"
                    
                    add_marker(location.latitude, location.longitude, name, popup_html, color, target_group)
                    processed_count += 1
                    continue # Success
                else:
                    print(f"  -> Not found: '{clean_addr}'")
    
            except Exception as e:
                print(f"  -> Error processing {name}: {e}")
    
        # Fallback: Try Geocoding by Name
        # Only if we really missed it
        print(f"  -> Falling back to geocoding by name: '{name} Berlin'")
        try:
            location = geocode(f"{name} Berlin")
            if location:
                    print(f"  -> Found by Name: {location.latitude}, {location.longitude}")
                    print(f"     [Debug] Type: {school_type} -> Color: {color}")
                    
                    popup_html = f"<b>{name}</b><br><i>{school_type}</i><br>Address: N/A (Geocoded by Name)<br>"
                    if homepage:
                        popup_html += f"<a href='{homepage}' target='_blank'>Homepage</a> | "
                    popup_html += f"<a href='{url}' target='_blank'>Schulprofil</a>"
                    
                    # Use the determined color even for fallback, but maybe flag it? 
                    # Original code used 'red' for fallback, but that conflicts with ISS color now. 
                    # Let's stick to the type color but maybe add a note in popup.
                    add_marker(location.latitude, location.longitude, name, popup_html, color, target_group)
                    processed_count += 1
            else:
                print("  -> Name geocoding failed.")
        except Exception as e:
            print(f"  -> Name geocoding error: {e}")

except KeyboardInterrupt:
    print("\nProcess interrupted by user. Saving partial map...")
finally:
    # Add layers to map
    gymnasium_group.add_to(m)
    iss_group.add_to(m)
    other_group.add_to(m)
    
    # Add Layer Control
    folium.LayerControl(collapsed=False).add_to(m)
    
    output_file = 'docs/index.html'
    m.save(output_file)
    print(f"Map saved to {output_file}. Plotted {processed_count} schools.")
