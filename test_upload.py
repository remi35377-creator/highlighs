import requests
import os

video_path = r'C:\Users\remid\Nextcloud3\Remi\Youtube\Aufnahmen\Oneblock\1.mp4'
file_size = os.path.getsize(video_path) / (1024*1024*1024)
print(f'Video Size: {file_size:.2f} GB')

with open(video_path, 'rb') as f:
    files = {'file': ('1.mp4', f, 'video/mp4')}
    print('Uploading...')
    r = requests.post('http://localhost:5000/api/upload', files=files, stream=True)
    print(f'Status: {r.status_code}')
    data = r.json()
    print(f'Video ID: {data.get("video_id")}')
    print(f'Status: {data.get("status")}')