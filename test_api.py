import requests
import time

time.sleep(2)
r = requests.get('http://localhost:8000/dashboard/market-overview?provider=yfinance', timeout=5)
print('HTTP Status:', r.status_code)
print('Response length:', len(r.text))
if r.status_code == 200:
    data = r.json()
    print('Indices:', len(data.get('indices', {}).get('items', [])))
    print('Followed:', len(data.get('followed', {}).get('items', [])))
    print('Valuation:', len(data.get('valuation_indicators', {}).get('items', [])))
else:
    print('Error:', r.text)
