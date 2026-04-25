import requests

video_path = r'C:\Users\remid\Nextcloud3\Remi\Youtube\Aufnahmen\MeldStudio_Recording_Recording_Output_2026-03-27_at_10.40.43pm.mp4'

with open(video_path, 'rb') as f:
    files = {'file': ('test.mp4', f)}
    r = requests.post('http://localhost:5000/api/upload', files=files)
    print('Status:', r.status_code)
    data = r.json()
    print('Video ID:', data.get('video_id'))
    vid = data.get('video_id')

if vid:
    import time
    for i in range(10):
        time.sleep(2)
        r = requests.get(f'http://localhost:5000/api/video/{vid}')
        v = r.json()
        print(f'Check {i+1}:', v.get('status'))
        if v.get('status') == 'completed':
            break
    
    r = requests.get(f'http://localhost:5000/api/video/{vid}/highlights')
    hl = r.json()
    print('Highlights gefunden:', len(hl))
    for h in hl[:3]:
        print(f'  - {h["title"]}: {h["start_time"]:.0f}s-{h["end_time"]:.0f}s (Score: {h["score"]:.0f})')