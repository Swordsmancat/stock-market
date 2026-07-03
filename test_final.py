import requests
import time

time.sleep(3)
print('正在请求市场看板数据（可能需要30秒下载指数数据）...')
r = requests.get('http://localhost:8000/dashboard/market-overview', params={'provider': 'yfinance'}, timeout=60)
print('Status:', r.status_code)
if r.status_code == 200:
    data = r.json()
    print('Indices:', len(data.get('indices', {}).get('items', [])))
    print('Followed:', len(data.get('followed', {}).get('items', [])))
    print('Valuation:', len(data.get('valuation_indicators', {}).get('items', [])))
    print('✅ 市场看板 API 正常工作！')
else:
    print('Error:', r.text)
