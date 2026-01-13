import requests
from bs4 import BeautifulSoup
import sys
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

url = "https://www.bildung.berlin.de/Schulverzeichnis/"
try:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    forms = soup.find_all('form')
    target_form = None
    gymnasium_value = None
    select_name = None

    for form in forms:
        selects = form.find_all('select')
        for s in selects:
            for opt in s.find_all('option'):
                if 'Gymnasium' in opt.text:
                    target_form = form
                    select_name = s.get('name')
                    gymnasium_value = opt.get('value')
                    break
            if target_form: break
        if target_form: break

    if not target_form:
        print("Could not find form with Gymnasium option")
        sys.exit(1)

    print(f"Found form. Action: {target_form.get('action')}")
    print(f"Select Name: {select_name}")
    print(f"Gymnasium Value: {gymnasium_value}")

    # Prepare data
    data = {}
    # Get all other inputs
    for inp in target_form.find_all('input'):
        name = inp.get('name')
        value = inp.get('value', '')
        if name:
            data[name] = value
    
    # Set the gymnasium value
    data[select_name] = gymnasium_value

    # Handle action URL
    action = target_form.get('action')
    if not action.startswith('http'):
        action = urllib.parse.urljoin(url, action)
    
    print(f"Submitting to: {action}")
    
    # Check method
    method = target_form.get('method', 'get').lower()
    
    if method == 'post':
        res = requests.post(action, data=data)
    else:
        res = requests.get(action, params=data)
    
    print(f"Response Status: {res.status_code}")
    print(f"Response URL: {res.url}")
    
    # Analyze results
    res_soup = BeautifulSoup(res.text, 'html.parser')
    # Count results - heuristic
    headers = res_soup.find_all(['h1', 'h2', 'h3', 'h4'])
    print("Headers found in response:")
    for h in headers[:5]:
        print(h.text.strip())

    # Look for list of schools
    links = res_soup.find_all('a')
    school_links = [l for l in links if 'Schulportrait' in l.get('href', '')]
    print(f"Found {len(school_links)} potential school links.")
    
    if len(school_links) > 0:
        print("First 3 links:")
        for l in school_links[:3]:
            print(f" - {l.text.strip()} -> {l.get('href')}")

except Exception as e:
    print(f"Error: {e}")
