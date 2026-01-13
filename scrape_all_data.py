import requests
from bs4 import BeautifulSoup
import json
import re
import time
import sys

# Force utf-8
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def extract_homepage(soup):
    # Look for "Internet" or "Homepage" label
    # Often in a row like "Internet: www.foo.de"
    
    # Text search
    text_soup = soup.get_text(separator=' ')
    
    # Regex for URL
    # Simple regex to find urls that might be the school's
    # We want to avoid internal links.
    # Often they are in an anchor tag near the label "Internet"
    
    label = soup.find(string=re.compile(r'Internet|Homepage|Webseite', re.I))
    if label:
        # Look at parent links or next siblings
        container = label.parent
        # Check if container is 'a'
        if container.name == 'a':
            return container.get('href')
        
        # Check next sibling
        nxt = container.find_next_sibling('a')
        if nxt:
            return nxt.get('href')
            
        # Check parent's next sibling (table cell)
        if container.parent.name == 'td':
             next_td = container.parent.find_next_sibling('td')
             if next_td:
                 a = next_td.find('a')
                 if a: return a.get('href')
                 # sometimes text only
                 return next_td.get_text().strip()

    return None

def extract_address(soup):
    # Heuristic 1: Look for "Anschrift" label
    # Often in a table row or div
    anschrift_label = soup.find(string=re.compile(r'Anschrift', re.I))
    if anschrift_label:
        # Try to get the next element or parent's sibling
        container = anschrift_label.parent
        # Go up until we find a block that might contain the address?
        # Or look for the next cell if it's a table
        if container.name == 'td':
            next_td = container.find_next_sibling('td')
            if next_td:
                 text = next_td.get_text(separator=' ').strip()
                 text = re.sub(r'\s+', ' ', text)
                 return text
        
        # If not table, maybe a definition list 'dt' 'dd'
        if container.name == 'dt':
            next_dd = container.find_next_sibling('dd')
            if next_dd:
                text = next_dd.get_text(separator=' ').strip()
                text = re.sub(r'\s+', ' ', text)
                return text

    # Heuristic 2: Look for 5 digit zip code "1[0-4][0-9]{3}" and "Berlin"
    text = soup.get_text(separator=' ')
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Regex: Look for zip code and Berlin
    # Capture preceding chars to get street
    # e.g. "Musterstr. 12 10115 Berlin"
    # Zip code for Berlin is range 10000 - 14999 roughly
    # Use greedy match for the prefix to capture full address line
    match = re.search(r'(.{15,100})\b(1\d{4})\s+Berlin', text)
    
    if match:
        full_string = match.group(0).strip()
        
        # Post-process cleanup
        
        # Remove "Stadtplan" and "Standort" which appear in the middle often
        full_string = re.sub(r'(Stadtplan|Standort)', '', full_string, flags=re.IGNORECASE)

        # Remove common labels if they were captured (assumed to be prefixes)
        for garbage in ['Anschrift', 'Telefon', 'Email', 'Web', 'Schulleitung', 'Dienststelle']:
             if garbage in full_string:
                 full_string = full_string.split(garbage)[-1].strip()
                 
        # Remove leading punctuation/digits if it looks like garbage (e.g. ": 12345 Berlin")
        full_string = full_string.lstrip(':-_ ')
        
        return full_string
        
    return None

data = []
with open('schools_list.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            name = parts[0]
            url = parts[1]
            school_type = parts[2] if len(parts) > 2 else 'Gymnasium'
            data.append({'name': name, 'url': url, 'school_type': school_type})

print(f"Scraping {len(data)} schools...")

results = []

import concurrent.futures
import threading

data = []
with open('schools_list.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            name = parts[0]
            url = parts[1]
            school_type = parts[2] if len(parts) > 2 else 'Gymnasium'
            data.append({'name': name, 'url': url, 'school_type': school_type})

print(f"Scraping {len(data)} schools with threading...")

results = []
lock = threading.Lock()
processed = 0

def process_school(school):
    global processed
    res_school = school.copy()
    try:
        # Create new session per thread or assume short lived
        # Better to just use requests.get with headers for simplicity in threads
        # or use a session if we pass it. Session is not thread safe by default? 
        # Actually requests.Session is thread safe.
        
        r = requests.get(school['url'], headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Address
            addr = extract_address(soup)
            if addr:
                addr = re.sub(r'\s+', ' ', addr)
                res_school['address'] = addr
            
            # Homepage
            web = extract_homepage(soup)
            if web:
                res_school['homepage'] = web
                
        else:
            print(f"Error {r.status_code} for {school['name']}")
            
    except Exception as e:
        print(f"Ex: {e} for {school['name']}")
    
    with lock:
        results.append(res_school)
        processed += 1
        if processed % 10 == 0:
            print(f"Processed {processed}/{len(data)}...")

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(process_school, data)

# Final save
with open('schools_data.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Done. Saved {len(results)} schools to schools_data.json")
