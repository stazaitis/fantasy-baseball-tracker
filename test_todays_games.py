import requests
from datetime import datetime

today = datetime.now().strftime("%Y-%m-%d")
url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"

res = requests.get(url)
data = res.json()

print(data)
