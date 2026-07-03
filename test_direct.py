import requests

print("Testing different endpoints:")
endpoints = [
    "/health",
    "/instruments",
    "/dashboard/market-overview?provider=yfinance",
]

for endpoint in endpoints:
    try:
        r = requests.get(f"http://localhost:8000{endpoint}", timeout=3)
        print(f"{endpoint}: {r.status_code}")
    except Exception as e:
        print(f"{endpoint}: ERROR - {e}")
