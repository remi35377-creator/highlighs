import requests

print('Testing upload...')
video_path = r'C:\Users\remid\Nextcloud3\Remi\Youtube\Aufnahmen\MeldStudio_Recording_Recording_Output_2026-03-27_at_10.40.43pm.mp4'

with open(video_path, 'rb') as f:
    files = {'file': ('test.mp4', f)}
    r = requests.post('http://localhost:5000/api/upload', files=files)
    print('Upload Status:', r.status_code)
    data = r.json()
    vid = data.get('video_id')
    print('Video ID:', vid)

if vid:
    import time
    print('Waiting for analysis...')
    for i in range(12):
        time.sleep(2)
        r = requests.get(f'http://localhost:5000/api/video/{vid}')
        v = r.json()
        print(f'  {i+1}: {v.get("status")}')
        if v.get('status') == 'completed':
            break
    
    r = requests.get(f'http://localhost:5000/api/video/{vid}/highlights')
    hl = r.json()
    print('Highlights:', len(hl))
    for h in hl[:5]:
        print(f'  - {h["title"]}: {h["start_time"]:.0f}s-{h["end_time"]:.0f}s (Score: {h["score"]:.0f})')
    print('SUCCESS!')
else:
    print('Error:', data)