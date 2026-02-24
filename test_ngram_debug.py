import requests
import json

url = "http://localhost:8000/api/ngrams/frequency?n=2&top_k=3"
response = requests.get(url, proxies={"http": None, "https": None})

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 500:
    try:
        error_detail = response.json()
        print(f"Error detail: {json.dumps(error_detail, indent=2)}")
    except:
        pass
