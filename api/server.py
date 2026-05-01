import os
import cv2
import numpy as np
import subprocess
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import uuid
from datetime import datetime
import threading
import json

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Echte Video-Analyse-Funktionen
def analyze_video_metrics(video_path):
    """Echtes Video analysieren mit OpenCV"""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    
    # Metriken sammeln
    pixel_changes = []
    motion_scores = []
    brightness_values = []
    face_detections = 0
    
    # Frames analysieren (jeden 10. Frame für Speed)
    frame_idx = 0
    prev_gray = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % 10 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Pixel-Änderungen
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                change = np.mean(diff)
                pixel_changes.append(change)
            
            # Helligkeit
            brightness = np.mean(gray)
            brightness_values.append(brightness)
            
            # Bewegung (große Änderungen = Bewegung)
            if prev_gray is not None:
                motion = np.std(diff)
                motion_scores.append(motion)
            
            prev_gray = gray
        
        frame_idx += 1
        if frame_idx > 500:  # Max 500 Frames für Speed
            break
    
    cap.release()
    
    # Ergebnisse berechnen
    avg_pixel = np.mean(pixel_changes) if pixel_changes else 0
    avg_motion = np.mean(motion_scores) if motion_scores else 0
    avg_brightness = np.mean(brightness_values) if brightness_values else 128
    
    # Normalisieren auf 0-100%
    pixel_score = min(100, int(avg_pixel / 2))
    motion_score = min(100, int(avg_motion / 5))
    brightness_score = int((avg_brightness / 255) * 100)
    contrast_score = min(100, int(np.std(brightness_values) / 20) if brightness_values else 50)
    
    # Szenen-Wechsel (große Helligkeitsänderungen)
    scene_changes = sum(1 for i in range(1, len(brightness_values)) 
                       if abs(brightness_values[i] - brightness_values[i-1]) > 30)
    scene_score = min(100, scene_changes * 10)
    
    return {
        'pixel': pixel_score,
        'motion': motion_score,
        'brightness': brightness_score,
        'contrast': contrast_score,
        'scene': scene_score,
        'duration': int(duration)
    }

def find_highlights(video_path, metrics):
    """Highlight-Clips finden basierend auf Metriken"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    
    # Simpler Highlight-Finder basierend auf Metriken
    highlights = []
    
    # Erstelle 3 Highlights
    for i in range(3):
        start = int((duration / 4) * (i + 1))
        end = min(start + 30, int(duration))
        
        # Score basierend auf Metriken
        score = 70 + (metrics['pixel'] // 10) + (metrics['motion'] // 10) - (i * 5)
        
        title = ['Action-Höhepunkt', 'Spannender Moment', 'Highlight'][i]
        
        highlights.append({
            'id': str(uuid.uuid4()),
            'start_time': start,
            'end_time': end,
            'score': score,
            'title': title,
            'metrics': {
                'pixel': metrics['pixel'],
                'motion': metrics['motion'],
                'brightness': metrics['brightness']
            }
        })
    
    return highlights

# Analyse im Hintergrund starten
def process_video_async(video_id, video_path, email):
    """Video im Hintergrund analysieren"""
    try:
        # Metriken analysieren
        metrics = analyze_video_metrics(video_path)
        
        if metrics:
            # Highlights finden
            highlights = find_highlights(video_path, metrics)
            
            # Ergebnisse speichern
            videos_db[video_id] = {
                'email': email,
                'filename': os.path.basename(video_path),
                'date': datetime.now().isoformat(),
                'status': 'completed',
                'metrics': metrics,
                'highlights': highlights
            }
        else:
            videos_db[video_id]['status'] = 'failed'
    except Exception as e:
        print(f"Error processing video: {e}")
        videos_db[video_id]['status'] = 'failed'

# In-Memory Database
videos_db = {}

HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Highlight AI</title>
    <style>
        body { font-family: Arial; background: #0a0a0f; color: #fff; padding: 20px; }
        .box { max-width: 400px; margin: 50px auto; padding: 30px; background: #15151f; border-radius: 10px; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #1a1a25; border: 1px solid #8b5cf6; color: #fff; }
        button { width: 100%; padding: 12px; background: #8b5cf6; border: none; color: #fff; cursor: pointer; border-radius: 8px; }
        #otp { display: none; }
        .main { display: none; }
    </style>
</head>
<body>
    <h1 style="text-align:center;">Highlight AI</h1>
    
    <div class="box" id="login">
        <h2>Login</h2>
        <input type="email" id="email" placeholder="E-Mail">
        <button onclick="send()">Code senden</button>
        <div id="otp">
            <input type="text" id="code" placeholder="Code">
            <button onclick="verify()">Bestätigen</button>
        </div>
    </div>
    
    <div class="main" id="main">
        <h2>Willkommen <span id="useremail"></span></h2>
        <button onclick="logout()">Abmelden</button>
        <h3>Video hochladen:</h3>
        <input type="file" id="file" onchange="upload()">
        <div id="status"></div>
    </div>

    <script>
    function send() {
        var e = document.getElementById('email').value;
        if(e.indexOf('@') === -1) { alert('E-Mail eingeben'); return; }
        var c = Math.floor(100000 + Math.random() * 900000);
        localStorage.setItem('code', c);
        localStorage.setItem('email', e);
        document.getElementById('otp').style.display = 'block';
        alert('Dein Code: ' + c);
    }
    function verify() {
        var i = document.getElementById('code').value;
        if(i == localStorage.getItem('code')) {
            document.getElementById('login').style.display = 'none';
            document.getElementById('main').style.display = 'block';
            document.getElementById('useremail').innerText = localStorage.getItem('email');
        } else {
            alert('Falscher Code');
        }
    }
    function logout() {
        localStorage.clear();
        location.reload();
    }
    function upload() {
        var f = document.getElementById('file').files[0];
        if(!f) return;
        document.getElementById('status').innerText = 'Wird hochgeladen...';
        var fd = new FormData();
        fd.append('file', f);
        fd.append('email', localStorage.getItem('email'));
        var x = new XMLHttpRequest();
        x.upload.onprogress = function(e) {
            if(e.lengthComputable) {
                document.getElementById('status').innerText = Math.round(e.loaded/e.total*100) + '%';
            }
        };
        x.onload = function() {
            if(x.status === 200) {
                document.getElementById('status').innerText = 'Hochgeladen! Video wird analysiert...';
            }
        };
        x.open('POST', '/api/upload');
        x.send(fd);
    }
    var saved = localStorage.getItem('email');
    if(saved) {
        document.getElementById('login').style.display = 'none';
        document.getElementById('main').style.display = 'block';
        document.getElementById('useremail').innerText = saved;
    }
    </script>
</body>
</html>'''

@app.route('/')
def home():
    return HTML

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    email = request.form.get('email', '')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    file = request.files['file']
    filename = file.filename[:100] if file.filename else 'video.mp4'
    
    video_id = str(uuid.uuid4())
    video_path = os.path.join(UPLOAD_FOLDER, video_id + '_' + filename)
    file.save(video_path)
    
    videos_db[video_id] = {
        'email': email,
        'filename': filename,
        'date': datetime.now().isoformat(),
        'status': 'processing'
    }
    
    # Video im Hintergrund analysieren
    threading.Thread(target=process_video_async, args=(video_id, video_path, email)).start()
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/video/<vid>')
def get_video(vid):
    if vid not in videos_db:
        return jsonify({'error': 'Not found'}), 404
    v = videos_db[vid]
    return jsonify({
        'id': vid,
        'filename': v['filename'],
        'status': v.get('status', 'processing'),
        'metrics': v.get('metrics'),
        'highlights': v.get('highlights', [])
    })

@app.route('/api/history/<email>')
def history(email):
    email = email.lower()
    videos = [{'id': vid, 'filename': v['filename'], 'date': v['date'][:10], 'status': v.get('status', 'processing')} 
             for vid, v in videos_db.items() if v.get('email', '').lower() == email]
    return jsonify(videos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)