import requests
from bs4 import BeautifulSoup
import sys

# Force utf-8
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "https://www.bildung.berlin.de/Schulverzeichnis/"
session = requests.Session()

try:
    print(f"Fetching {BASE_URL}...")
    response = session.get(BASE_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("\n--- Schulart Options ---")
    forms = soup.find_all('form')
    for form in forms:
        selects = form.find_all('select')
        for s in selects:
            # Check if this select has 'Gymnasium' as an option to identify it
            options = s.find_all('option')
            # Just print all options if it looks like the Schulart dropdown (usually has > 10 options or contains Gymnasium)
            if any('Gymnasium' in opt.text for opt in options):
                with open('types_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"--- Schulart Select found: {s.get('name')} ---\n")
                    for opt in options:
                        f.write(f"ID: {opt.get('value')} | Text: {opt.text.strip()}\n")
                break
        else:
            continue
        break
        
except Exception as e:
    print(f"Error: {e}")
