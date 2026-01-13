import requests
from bs4 import BeautifulSoup
import urllib.parse
import sys

# User provided headers
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-GB,en;q=0.9,en-US;q=0.8,de;q=0.7',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    # 'Content-Length': '5301', # Request lib handles this
    'Content-Type': 'application/x-www-form-urlencoded',
    'DNT': '1',
    'Origin': 'https://www.bildung.berlin.de', # Fixed origin
    'Referer': 'https://www.bildung.berlin.de/Schulverzeichnis/', # Added referer
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
    'sec-ch-ua': '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

session = requests.Session()
session.headers.update(HEADERS)

BASE_URL = "https://www.bildung.berlin.de/Schulverzeichnis/"

def get_form_data(target_type_str="Gymnasium"):
    print(f"Fetching {BASE_URL}...")
    try:
        response = session.get(BASE_URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching base page: {e}")
        sys.exit(1)
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    target_form = None
    schulart_select_name = None
    schulart_value = None
    
    forms = soup.find_all('form')
    # print(f"Found {len(forms)} forms.")
    
    for form in forms:
        selects = form.find_all('select')
        for s in selects:
             # Check options for target type
             for opt in s.find_all('option'):
                 if target_type_str in opt.text:
                     target_form = form
                     schulart_select_name = s.get('name')
                     schulart_value = opt.get('value')
                     print(f"Found target form with select '{schulart_select_name}' and value '{schulart_value}' for '{target_type_str}'")
                     break
             if target_form: break
        if target_form: break
    
    if not target_form:
        if forms:
            target_form = forms[0]
            print("Could not find specific form, using first form as fallback.")
        else:
            print("No forms found!")
            sys.exit(1)

    # Calculate Action URL
    action = target_form.get('action')
    # print(f"Raw action: {action}")
    
    if not action:
        action_url = BASE_URL
    elif action.startswith('http'):
        action_url = action
    else:
        action_url = urllib.parse.urljoin(BASE_URL, action)
        
    # print(f"Resolved Action URL: {action_url}")

    data = {}
    
    # Collect all inputs
    for inp in target_form.find_all('input'):
        name = inp.get('name')
        value = inp.get('value', '')
        if name:
            data[name] = value

    # Identify special selects
    # We return the schulart key/value to be set by caller
    # But checking for Bezirk is still needed if we want to set it default
    
    bezirk_name = None
    for select in target_form.find_all('select'):
        name = select.get('name', '')
        if 'Bezirk' in name:
            bezirk_name = name
            
    if bezirk_name:
        # print(f"Setting {bezirk_name} to 0 (All Regions)")
        data[bezirk_name] = '0'
    else:
         data['ctl00$ContentPlaceHolder1$DropDownListBezirk'] = '0'
    
    # Check for submitting button
    submit_buttons = target_form.find_all('input', type='submit')
    for btn in submit_buttons:
        val = btn.get('value', '').lower()
        if 'such' in val or 'find' in val:
            data[btn.get('name')] = btn.get('value')
            break
            
    return action_url, data, schulart_select_name, schulart_value

def perform_search(action_url, data):
    print(f"Submitting search to {action_url}...")
    try:
        response = session.post(action_url, data=data)
        response.raise_for_status()
        print(f"Search response code: {response.status_code}")
        return response
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        # Print first 500 chars of response to see if it's an ASP.NET error page
        print(e.response.text[:500])
        sys.exit(1)

def parse_results(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # The user wants "all schools ... with their addresses"
    # We need to see how the list looks.
    # Usually links to details.
    
    results = []
    
    # Look for links that contain 'Schulportrait'
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link['href']
        if 'Schulportrait' in href and 'ID' in href:
            name = link.text.strip()
            # Clean up name
            name = " ".join(name.split())
            
            full_url = urllib.parse.urljoin(BASE_URL, href)
            
            # Use a dict to dedup by URL
            results.append({
                'name': name,
                'url': full_url
            })
            
    # Deduplicate
    unique_results = []
    seen_urls = set()
    for r in results:
        if r['url'] not in seen_urls:
            seen_urls.add(r['url'])
            unique_results.append(r)
            
    print(f"Found {len(unique_results)} schools.")
    return unique_results

if __name__ == "__main__":
    # Ensure stdout is utf-8
    sys.stdout.reconfigure(encoding='utf-8')
    
    # Define target school types to scrape
    # We search for options containing these strings
    # "Gymnasien" matches ID 14. "Gymnasium" matches "Berufliches Gymnasium" (ID 36) which comes first.
    TARGET_TYPES = ["Gymnasien", "Integrierte Sekundarschule"]
    
    all_results = []
    
    # We need to find the form once, then reuse it or re-fetch for each type if needed.
    # Re-fetching is safer to get fresh state (ASP.NET viewstate etc)
    
    for school_type_name in TARGET_TYPES:
        print(f"\n--- Processing: {school_type_name} ---")
        
        # Fresh session/page load for each search to avoid state issues
        session.cookies.clear() 
        action_url, form_data, schulart_key, schulart_val = get_form_data(target_type_str=school_type_name)
        
        if not schulart_key:
            print(f"Skipping {school_type_name} (option not found).")
            continue
            
        # Set the specific school type value
        print(f"Setting {schulart_key} to {schulart_val} ({school_type_name})")
        form_data[schulart_key] = schulart_val
        
        # Perform search
        res = perform_search(action_url, form_data)
        schools = parse_results(res.text)
        
        # Tag with type
        for s in schools:
            s['type'] = school_type_name
            # simplified type name for file/ui
            if "Gymnasien" in school_type_name or "Gymnasium" in school_type_name:
                s['simple_type'] = "Gymnasium"
            elif "Sekundarschule" in school_type_name:
                 s['simple_type'] = "ISS"
            else:
                 s['simple_type'] = "Other"
            
            all_results.append(s)

    # Deduplicate by URL (in case school appears in both, though unlikely)
    unique_map = {}
    for s in all_results:
        # If already exists, maybe append type? e.g. "Gymnasium / ISS"
        if s['url'] in unique_map:
            existing = unique_map[s['url']]
            if s['simple_type'] not in existing['simple_type']:
                 existing['simple_type'] += f" / {s['simple_type']}"
        else:
            unique_map[s['url']] = s
            
    final_schools = list(unique_map.values())
    print(f"\nTotal unique schools found: {len(final_schools)}")

    # Save the output to a file for review
    # Format: Name \t URL \t Type
    with open('schools_list.txt', 'w', encoding='utf-8') as f:
        for s in final_schools:
            f.write(f"{s['name']}\t{s['url']}\t{s['simple_type']}\n")
            
    if not final_schools:
         print("No schools found. Debugging...")
         # ... existing debug handling ...
