import urllib.request
import urllib.error
import json
import base64

# The raw JSON expense data we want to send
expense_data = {
    "amount": 150.0,
    "submitter": "alice@company.com",
    "category": "software",
    "description": "IDE License",
    "date": "2026-06-06"
}

# 1. Pub/Sub requires the data to be a string encoded in Base64
json_str = json.dumps(expense_data)
encoded_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

# 2. Build the standard Pub/Sub Push payload format
pubsub_payload = {
    "message": {
        "data": encoded_data,
        "attributes": {
            "source": "local_testing"
        }
    },
    "subscription": "projects/my-project/subscriptions/expense-test-sub"
}

# 3. Send it to your local ambient server via POST
url = "http://localhost:8080/apps/expense_agent/trigger/pubsub"
data = json.dumps(pubsub_payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

print(f"Enviando evento simulado de Pub/Sub a {url}...")
try:
    with urllib.request.urlopen(req) as response:
        result = response.read().decode('utf-8')
        print(f"\n¡Éxito! El servidor respondió: {response.status}")
        print(f"Respuesta: {result}")
except urllib.error.URLError as e:
    print(f"\nError: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
