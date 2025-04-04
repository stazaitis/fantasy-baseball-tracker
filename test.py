import requests

url = "https://fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/121956?view=mTeam"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Cookie": "espn_s2=AEBZCH477i9TIcogL%2F...your_real_cookie...; SWID={213A1465-...}",
    "x-fantasy-filter": "{}"
}

res = requests.get(url, headers=headers)

try:
    data = res.json()
    print("✅ JSON Loaded")
    print(data)
except Exception as e:
    print("❌ Still HTML. Status code:", res.status_code)
    print(res.text[:500])
