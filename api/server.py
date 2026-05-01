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
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0f; color: #fff; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { display: flex; justify-content: space-between; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: #888; font-size: 18px; }
        .login-box { max-width: 400px; margin: 40px auto; padding: 40px; background: #15151f; border-radius: 16px; }
        .login-input { width: 100%; padding: 16px; margin-bottom: 16px; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); border-radius: 10px; color: #fff; font-size: 16px; box-sizing: border-box; }
        .login-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border: none; border-radius: 10px; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; box-sizing: border-box; }
        .otp-input { width: 100%; padding: 16px; margin-bottom: 16px; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); border-radius: 10px; color: #fff; font-size: 24px; text-align: center; letter-spacing: 8px; font-family: monospace; box-sizing: border-box; }
        .otp-section { display: none; margin-top: 24px; }
        .user-bar { display: flex; align-items: center; gap: 12px; }
        .user-email { font-size: 14px; color: #888; }
        .logout-btn { padding: 8px 16px; background: transparent; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; color: #888; cursor: pointer; }
        .upload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }
        .upload-card { background: #15151f; border: 2px dashed rgba(139,92,246,0.4); border-radius: 16px; padding: 40px; text-align: center; cursor: pointer; }
        .upload-card:hover { border-color: #8b5cf6; }
        .upload-card-icon { font-size: 40px; margin-bottom: 12px; }
        .upload-card h3 { font-size: 16px; margin-bottom: 8px; }
        .upload-card p { font-size: 13px; color: #888; }
        .progress { display: none; margin-top: 30px; padding: 24px; background: #15151f; border-radius: 16px; }
        .progress.active { display: block; }
        .progress-fill { height: 8px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 4px; width: 0%; }
        .dashboard { display: none; margin-top: 40px; }
        .dashboard.active { display: block; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
        .metric-card { background: #15151f; border-radius: 14px; padding: 20px; }
        .metric-title { font-size: 13px; color: #888; margin-bottom: 8px; }
        .metric-value { font-size: 28px; font-weight: 700; color: #8b5cf6; }
        .highlights-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .highlight-card { background: #15151f; border-radius: 14px; overflow: hidden; }
        .highlight-video { height: 140px; background: #1a1a25; display: flex; align-items: center; justify-content: center; position: relative; }
        .highlight-duration { position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.8); padding: 4px 8px; border-radius: 6px; }
        .highlight-score { position: absolute; top: 10px; left: 10px; background: rgba(139,92,246,0.9); padding: 6px 10px; border-radius: 8px; }
        .highlight-content { padding: 16px; }
        .highlight-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
        .action-btn { display: block; width: 100%; padding: 10px; margin-top: 10px; background: #8b5cf6; border: none; border-radius: 8px; color: #fff; cursor: pointer; }
        .history-section { margin-top: 60px; }
        .history-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .history-card { background: #15151f; border-radius: 14px; padding: 16px; cursor: pointer; }
        .history-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
        .history-date { font-size: 12px; color: #888; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px; }
        .status-processing { background: #f59e0b; color: #000; }
        .status-completed { background: #10b981; color: #fff; }
        input[type="file"] { display: none; }
        @media (max-width: 768px) { .upload-grid, .metrics-grid, .highlights-grid, .history-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo"><div class="logo-icon">⚡</div><div class="logo-text">Highlight AI</div></div>
            <div class="user-bar" id="user-bar"></div>
        </header>
        
        <main>
            <div class="hero">
                <h1>Extrahiere die <span class="highlight">perfekten Momente</span></h1>
                <p>KI-gestützte Video-Analyse</p>
            </div>
            
            <div class="login-box" id="login-box">
                <h2 style="margin-bottom:24px;text-align:center;">🔐 Anmelden</h2>
                <input type="email" id="email-input" class="login-input" placeholder="Deine E-Mail-Adresse" />
                <button type="button" class="login-btn" id="send-btn" onclick="sendCode()">Code senden</button>
                
                <div class="otp-section" id="otp-section">
                    <p style="color:#888;margin-bottom:16px;text-align:center;">Gib den Code ein, den du per E-Mail erhalten hast</p>
                    <input type="text" id="otp-input" class="otp-input" placeholder="XXXXXX" maxlength="6" />
                    <button type="button" class="login-btn" id="verify-btn" onclick="verifyCode()">Bestätigen</button>
                </div>
            </div>
            
            <div id="main-content" style="display:none;">
                <div class="upload-grid">
                    <div class="upload-card" onclick="document.getElementById('file').click()">
                        <div class="upload-card-icon">💾</div><h3>Dateiupload</h3><p>Von deinem Gerät</p>
                    </div>
                    <div class="upload-card" id="upload-url">
                        <div class="upload-card-icon">🔗</div><h3>URL Import</h3><p>Von Web-URL</p>
                    </div>
                    <div class="upload-card">
                        <div class="upload-card-icon">☁️</div><h3>Cloud Import</h3><p>Google Drive, etc.</p>
                    </div>
                </div>
                
                <input type="file" id="file" accept="video/*" />
                
                <div class="progress" id="progress">
                    <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                        <span id="progress-filename"></span>
                        <span id="progress-status">Wird analysiert...</span>
                        <span id="progress-percent" style="color:#8b5cf6;">0%</span>
                    </div>
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                
                <div class="dashboard" id="dashboard">
                    <div class="metrics-grid">
                        <div class="metric-card"><div class="metric-title">Pixel</div><div class="metric-value" id="m-pixel">0%</div></div>
                        <div class="metric-card"><div class="metric-title">Bewegung</div><div class="metric-value" id="m-motion">0%</div></div>
                        <div class="metric-card"><div class="metric-title">Helligkeit</div><div class="metric-value" id="m-brightness">0%</div></div>
                        <div class="metric-card"><div class="metric-title">Kontrast</div><div class="metric-value" id="m-contrast">0%</div></div>
                        <div class="metric-card"><div class="metric-title">Szenen</div><div class="metric-value" id="m-scene">0%</div></div>
                        <div class="metric-card"><div class="metric-title">Dauer</div><div class="metric-value" id="m-duration">0s</div></div>
                    </div>
                    <h2 style="margin-bottom:20px;">Highlights</h2>
                    <div class="highlights-grid" id="highlights-grid"></div>
                </div>
                
                <div class="history-section">
                    <h2>📺 Meine Videos</h2>
                    <div class="history-grid" id="history-grid"></div>
                </div>
            </div>
        </main>
    </div>
    
<script>
        var user = null;
        var currentVideoId = null;
        
        function sendCode() {
            var email = document.getElementById('email-input').value;
            if (!email || email.indexOf('@') === -1) { 
                alert('Bitte E-Mail eingeben'); 
                return; 
            }
            var code = Math.floor(100000 + Math.random() * 900000).toString();
            localStorage.setItem('verify_code', code);
            localStorage.setItem('verify_email', email);
            document.getElementById('otp-section').style.display = 'block';
            document.getElementById('send-btn').textContent = 'Code gesendet!';
            alert('Demo: Dein Code ist ' + code);
        }
        
        function verifyCode() {
            var inputCode = document.getElementById('otp-input').value;
            var storedCode = localStorage.getItem('verify_code');
            var email = localStorage.getItem('verify_email');
            
            if (inputCode === storedCode) {
                user = {email: email};
                localStorage.setItem('user_email', email);
                showLoggedIn();
            } else {
                alert('Falscher Code!');
            }
        }
        
        function logout() {
            localStorage.clear();
            user = null;
            location.reload();
        }
        
        function showLoggedIn() {
            document.getElementById('login-box').style.display = 'none';
            document.getElementById('main-content').style.display = 'block';
            document.getElementById('user-bar').innerHTML = '<span class="user-email">' + user.email + '</span><button class="logout-btn" onclick="logout()">Abmelden</button>';
            loadHistory();
        }
        
        function loadHistory() {
            fetch('/api/history/' + user.email)
            .then(function(r) { return r.json(); })
            .then(function(videos) {
                var grid = document.getElementById('history-grid');
                if (videos.length === 0) {
                    grid.innerHTML = '<p style="color:#888;">Noch keine Videos</p>';
                } else {
                    var html = '';
                    for (var i = 0; i < videos.length; i++) {
                        html += '<div class="history-card" data-id="' + videos[i].id + '"><div class="history-title">' + videos[i].filename + '</div><div class="history-date">' + videos[i].date + '</div></div>';
                    }
                    grid.innerHTML = html;
                    var cards = document.querySelectorAll('.history-card');
                    for (var j = 0; j < cards.length; j++) {
                        cards[j].addEventListener('click', function() {
                            loadVideo(this.getAttribute('data-id'));
                        });
                    }
                }
            });
        }
        
        function loadVideo(vid) {
            currentVideoId = vid;
            document.getElementById('dashboard').classList.add('active');
            loadHighlights(vid);
        }
        
        function handleFile(e) {
            var file = e.target.files[0];
            if (!file) return;
            
            document.getElementById('progress').classList.add('active');
            document.getElementById('progress-filename').textContent = file.name;
            
            var formData = new FormData();
            formData.append('file', file);
            formData.append('email', user.email);
            
            var xhr = new XMLHttpRequest();
            xhr.upload.onprogress = function(evt) {
                if (evt.lengthComputable) {
                    var percent = Math.round((evt.loaded / evt.total) * 100);
                    document.getElementById('progress-percent').textContent = percent + '%';
                    document.getElementById('progress-fill').style.width = percent + '%';
                    if (percent === 100) {
                        document.getElementById('progress-status').textContent = 'Wird analysiert...';
                    }
                }
            };
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    currentVideoId = data.video_id;
                    var pollInt = setInterval(function() {
                        fetch('/api/video/' + currentVideoId)
                        .then(function(r) { return r.json(); })
                        .then(function(v) {
                            if (v.status === 'completed') {
                                clearInterval(pollInt);
                                document.getElementById('progress').classList.remove('active');
                                loadHighlights(currentVideoId);
                                loadHistory();
                            }
                        });
                    }, 2000);
                }
            };
            xhr.open('POST', '/api/upload');
            xhr.send(formData);
        }
        
        function loadHighlights(vid) {
            fetch('/api/video/' + vid)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                document.getElementById('dashboard').classList.add('active');
                
                if (data.metrics) {
                    document.getElementById('m-pixel').textContent = (data.metrics.pixel || 0) + '%';
                    document.getElementById('m-motion').textContent = (data.metrics.motion || 0) + '%';
                    document.getElementById('m-brightness').textContent = (data.metrics.brightness || 0) + '%';
                    document.getElementById('m-contrast').textContent = (data.metrics.contrast || 0) + '%';
                    document.getElementById('m-scene').textContent = (data.metrics.scene || 0) + '%';
                    document.getElementById('m-duration').textContent = (data.metrics.duration || 0) + 's';
                }
                
                var grid = document.getElementById('highlights-grid');
                if (data.highlights && data.highlights.length > 0) {
                    var html = '';
                    for (var i = 0; i < data.highlights.length; i++) {
                        var h = data.highlights[i];
                        var dur = h.end_time - h.start_time;
                        var min = Math.floor(dur / 60);
                        var sec = Math.floor(dur % 60);
                        html += '<div class="highlight-card"><div class="highlight-video"><div style="font-size:40px;">▶</div><div class="highlight-duration">' + min + ':' + (sec < 10 ? '0' : '') + sec + '</div><div class="highlight-score">Score: ' + h.score + '</div></div><div class="highlight-content"><div class="highlight-title">' + h.title + '</div><button class="action-btn">⬇️ Download</button></div></div>';
                    }
                    grid.innerHTML = html;
                } else {
                    grid.innerHTML = '<p style="color:#888;">Keine Highlights gefunden</p>';
                }
            });
        }
        
        function showUrlInput() {
            var url = prompt('Video URL:');
            if (url) {
                alert('URL-Upload coming soon!');
            }
        }
        
        document.getElementById('upload-url').addEventListener('click', showUrlInput);
        document.getElementById('file').addEventListener('change', handleFile);
        
        var savedEmail = localStorage.getItem('user_email');
        if (savedEmail) {
            user = {email: savedEmail};
            showLoggedIn();
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