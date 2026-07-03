import sys
sys.path.insert(0, r'E:\stock market')
from apps.api.main import app

print("All registered routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"  {route.methods} {route.path}")
