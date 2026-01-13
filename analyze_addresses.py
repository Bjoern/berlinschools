import json
import re

with open('schools_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total schools: {len(data)}")
addresses = [x.get('address') for x in data if x.get('address')]
print(f"Schools with address strings: {len(addresses)}")

# Analyze patterns
print("\nSample addresses:")
for a in addresses[:10]:
    print(f"'{a}'")

print("\n--- Potential Issues ---")
cnt_garbage = 0
for a in addresses:
    # Check if starts with code like 09Y02
    if re.match(r'^\s*[-]?\s*[0-9]{2}[A-Z][0-9]{2}', a):
        cnt_garbage += 1
    elif re.match(r'^\s*[-]?\s*[\d]+', a): # Starts with number
        pass 
        
print(f"Addresses starting with school code/garbage: {cnt_garbage}")
