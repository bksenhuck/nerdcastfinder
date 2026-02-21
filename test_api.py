import requests
import json

response = requests.get('http://localhost:8000/api/search?q=china&top_k=1')
data = response.json()

if data:
    print("\nFull API Response:")
    print(json.dumps(data[0], indent=2, ensure_ascii=False))
