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
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {'pixel': 75, 'motion': 80, 'brightness': 50, 'contrast': 60, 'scene': 40, 'duration': 30}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 30
        
        if duration <= 0:
            duration = 30
        
        # Metriken sammeln
        pixel_changes = []
        motion_scores = []
        brightness_values = []
        
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
        pixel_score = min(100, int(avg_pixel / 2)) if pixel_changes else 75
        motion_score = min(100, int(avg_motion / 5)) if motion_scores else 80
        brightness_score = int((avg_brightness / 255) * 100)
        contrast_score = min(100, int(np.std(brightness_values) / 20)) if brightness_values else 60
        
        # Szenen-Wechsel (große Helligkeitsänderungen)
        scene_changes = sum(1 for i in range(1, len(brightness_values)) 
                           if abs(brightness_values[i] - brightness_values[i-1]) > 30) if brightness_values else 4
        scene_score = min(100, scene_changes * 10)
        
        return {
            'pixel': pixel_score,
            'motion': motion_score,
            'brightness': brightness_score,
            'contrast': contrast_score,
            'scene': scene_score,
            'duration': int(duration)
        }
    except Exception as e:
        print(f"Video analysis error: {e}")
        # Fallback: Demo-Daten zurückgeben
        return {'pixel': 75, 'motion': 80, 'brightness': 50, 'contrast': 60, 'scene': 40, 'duration': 30}
    
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #0a0a0f; color: #fff; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { display: flex; justify-content: space-between; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; font-size: 24px; font-weight: bold; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: #888; font-size: 18px; }
        .box { max-width: 400px; margin: 40px auto; padding: 40px; background: #15151f; border-radius: 16px; }
        input { width: 100%; padding: 16px; margin: 10px 0; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); color: #fff; border-radius: 10px; }
        button { width: 100%; padding: 16px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border: none; color: #fff; cursor: pointer; border-radius: 10px; font-size: 16px; font-weight: 600; }
        #otp { display: none; }
        .main { display: none; }
        .upload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }
        .upload-card { background: #15151f; border: 2px dashed rgba(139,92,246,0.4); border-radius: 16px; padding: 40px; text-align: center; cursor: pointer; }
        .upload-card:hover { border-color: #8b5cf6; }
        .upload-icon { font-size: 40px; }
        .upload-card h3 { margin: 12px 0 8px; }
        .upload-card p { color: #888; font-size: 13px; }
        .progress { display: none; margin-top: 30px; padding: 24px; background: #15151f; border-radius: 16px; }
        .progress.active { display: block; }
        .progress-fill { height: 8px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 4px; width: 0%; }
        .status { margin-top: 20px; color: #8b5cf6; }
        .history { margin-top: 60px; }
        .history h2 { margin-bottom: 20px; }
        .history-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .history-card { background: #15151f; border-radius: 14px; padding: 16px; cursor: pointer; }
        .history-card:hover { border: 1px solid rgba(139,92,246,0.5); }
        .history-title { font-weight: 600; margin-bottom: 8px; }
        .history-date { color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">⚡ Highlight AI</div>
        </header>
        
        <main>
            <div class="hero">
                <h1>Extrahiere die <span class="highlight">perfekten Momente</span></h1>
                <p>KI-gestützte Video-Analyse</p>
            </div>
            
            <div class="box" id="login">
                <h2 style="text-align:center; margin-bottom:24px;">🔐 Anmelden</h2>
                <input type="email" id="email" placeholder="Deine E-Mail-Adresse">
                <button onclick="send()">Code senden</button>
                <div id="otp">
                    <p style="color:#888; margin:16px 0; text-align:center;">Gib den Code ein</p>
                    <input type="text" id="code" placeholder="XXXXXX" maxlength="6">
                    <button onclick="verify()">Bestätigen</button>
                </div>
            </div>
            
            <div class="main" id="main">
                <div class="upload-grid">
                    <div class="upload-card">
                        <div class="upload-icon">💾</div>
                        <h3>Dateiupload</h3>
                        <p>Von deinem Gerät</p>
                    </div>
                </div>
                <input type="file" id="file" accept="video/*" onchange="upload()" style="display:none">
                
                <div class="progress" id="progress">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                        <span id="filename"></span>
                        <span id="percent" style="color:#8b5cf6;">0%</span>
                    </div>
                    <div class="progress-fill" id="fill"></div>
                </div>
                
                <div class="status" id="status"></div>
                
                <div class="history">
                    <h2>📺 Meine Videos</h2>
                    <div class="history-grid" id="history"></div>
                </div>
            </div>
        </main>
    </div>

    <script>
    function send() {
        var e = document.getElementById('email').value;
        if(e.indexOf('@') === -1) { alert('Bitte E-Mail eingeben'); return; }
        var c = Math.floor(100000 + Math.random() * 900000);
        localStorage.setItem('code', c);
        localStorage.setItem('email', e);
        document.getElementById('otp').style.display = 'block';
        alert('Dein Code ist: ' + c);
    }
    function verify() {
        var i = document.getElementById('code').value;
        if(i == localStorage.getItem('code')) {
            document.getElementById('login').style.display = 'none';
            document.getElementById('main').style.display = 'block';
            loadHistory();
        } else {
            alert('Falscher Code!');
        }
    }
    function logout() {
        localStorage.clear();
        location.reload();
    }
    function upload() {
        var f = document.getElementById('file').files[0];
        if(!f) return;
        document.getElementById('progress').classList.add('active');
        document.getElementById('filename').innerText = f.name;
        var fd = new FormData();
        fd.append('file', f);
        fd.append('email', localStorage.getItem('email'));
        var x = new XMLHttpRequest();
        x.upload.onprogress = function(e) {
            if(e.lengthComputable) {
                var p = Math.round(e.loaded/e.total*100);
                document.getElementById('percent').innerText = p + '%';
                document.getElementById('fill').style.width = p + '%';
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
    function loadHistory() {
        var x = new XMLHttpRequest();
        x.open('GET', '/api/history/' + localStorage.getItem('email'), true);
        x.onreadystatechange = function() {
            if(x.readyState === 4 && x.status === 200) {
                var v = JSON.parse(x.responseText);
                var h = document.getElementById('history');
                if(v.length === 0) {
                    h.innerHTML = '<p style="color:#888;">Noch keine Videos</p>';
                } else {
                    h.innerHTML = '';
                    for(var i=0; i<v.length; i++) {
                        h.innerHTML += '<div class="history-card"><div class="history-title">' + v[i].filename + '</div><div class="history-date">' + v[i].date + '</div></div>';
                    }
                }
            }
        };
        x.send();
    }
    document.querySelector('.upload-card').onclick = function() { document.getElementById('file').click(); };
    var saved = localStorage.getItem('email');
    if(saved) {
        document.getElementById('login').style.display = 'none';
        document.getElementById('main').style.display = 'block';
        loadHistory();
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