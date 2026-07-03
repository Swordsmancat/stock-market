import sys
sys.path.insert(0, r'E:\stock market')

from apps.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

response = client.get("/dashboard/market-overview?provider=yfinance")
print("Status Code:", response.status_code)
print("Response:", response.json())
print("Indices:", len(response.json().get('indices', {}).get('items', [])))
print("Followed:", len(response.json().get('followed', {}).get('items', [])))
