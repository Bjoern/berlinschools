import requests
from bs4 import BeautifulSoup
import sys

# Force utf-8
sys.stdout.reconfigure(encoding='utf-8')

# Find specific school
target_name = "Albert-Einstein-Gymnasium"
found = False
with open('schools_list.txt', 'r', encoding='utf-8') as f:
    for line in f:
        if target_name in line:
             name, url = line.strip().split('\t')
             found = True
             break
if not found:
    print("School not found")
    sys.exit(1)

print(f"Inspecting: {name}")
print(f"URL: {url}")

try:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Dump removed for brevity
    # print(soup.get_text()[:2000])
    
    # Try to find common address containers
    # "Straße", "PLZ", "Ort" etc.
    
    print("\n--- Searching for address clues ---")
    text = soup.get_text(separator='\n')
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if 'Anschrift' in line:
            print(f"MATCH at line {i}: {line.strip()}")
            # Print next 10 lines
            for j in range(1, 11):
                if i+j < len(lines):
                    print(f"  +{j}: '{lines[i+j].strip()}'")
        
        # Also look for zip codes
        import re
        if re.search(r'\b1\d{4}\b', line):
             print(f"ZIP MATCH at line {i}: {line.strip()}")
        
        if 'Web' in line or 'Homepage' in line or 'Internet' in line:
             print(f"WEB MATCH at line {i}: {line.strip()}")
             for j in range(1, 3):
                if i+j < len(lines):
                    print(f"  +{j}: '{lines[i+j].strip()}'")

except Exception as e:
    print(f"Error: {e}")
