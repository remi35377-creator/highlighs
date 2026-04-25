import requests
vid = 'cd9ffb79-9bde-425f-9961-aebe4971e7b2'

r = requests.get(f'http://localhost:5000/api/video/{vid}')
print('Video Status:', r.json().get('status'))

r2 = requests.get(f'http://localhost:5000/api/video/{vid}/highlights')
data = r2.json()
print('Highlights:', len(data))
for h in data:
    print(f'  - {h["title"]}: {h["start_time"]:.0f}s-{h["end_time"]:.0f}s (Score: {h["score"]:.0f})')