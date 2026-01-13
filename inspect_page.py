import requests
from bs4 import BeautifulSoup
import sys

# Force utf-8 printing
sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.bildung.berlin.de/Schulverzeichnis/"
try:
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    forms = soup.find_all('form')
    print(f"Found {len(forms)} forms.")
    
    for i, form in enumerate(forms):
        # check if this form has the Gymnasium option
        has_gymnasium = False
        selects = form.find_all('select')
        for s in selects:
             if s.find('option', string=lambda t: t and 'Gymnasium' in t):
                 has_gymnasium = True
                 break
        
        if has_gymnasium:
            print(f"\n--- RELEVANT FORM ({i+1}) ---")
            print(f"Action: {form.get('action')}")
            print(f"Method: {form.get('method')}")
            
            inputs = form.find_all(['input', 'select', 'button'])
            for inp in inputs:
                name = inp.get('name')
                id_ = inp.get('id')
                type_ = inp.get('type')
                print(f"  Input: tag={inp.name}, name={name}, id={id_}, type={type_}")
                if inp.name == 'select':
                    options = inp.find_all('option')
                    print(f"    Select '{name}' has {len(options)} options.")
                    for opt in options:
                        if 'Gymnasium' in opt.text:
                            print(f"    -> FOUND Gymnasium: value='{opt.get('value')}', text='{opt.text.strip()}'")
        else:
             print(f"Form {i+1} does not seem to have Gymnasium selection.")

except Exception as e:
    print(f"Error: {e}")
