import requests

video_path = r'C:\Users\remid\Nextcloud3\Remi\Youtube\Aufnahmen\MeldStudio_Recording_Recording_Output_2026-03-27_at_10.40.43pm.mp4'
print('Uploading 30MB video...')

with open(video_path, 'rb') as f:
    files = {'file': ('test.mp4', f, 'video/mp4')}
    r = requests.post('http://localhost:5000/api/upload', files=files)
    print('Status:', r.status_code)
    data = r.json()
    print('Video ID:', data.get('video_id', data.get('error')))