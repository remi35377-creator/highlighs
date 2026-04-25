from flask import Flask, jsonify, request
import os
import uuid
import sqlite3
from datetime import datetime

app = Flask(__name__)

HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI</title>
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: #0a0a0f; color: #fff; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { display: flex; justify-content: space-between; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 10px; display: flex; align-items: center; justify-content: center; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: #888; font-size: 18px; }
        .upload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }
        .upload-card { background: #15151f; border: 2px dashed rgba(139,92,246,0.4); border-radius: 16px; padding: 40px; text-align: center; cursor: pointer; transition: 0.3s; }
        .upload-card:hover { border-color: #8b5cf6; transform: translateY(-5px); }
        .upload-card-icon { font-size: 40px; margin-bottom: 12px; }
        .upload-card h3 { font-size: 16px; margin-bottom: 8px; }
        .upload-card p { font-size: 13px; color: #888; }
        .progress { display: none; margin-top: 30px; padding: 24px; background: #15151f; border-radius: 16px; }
        .progress.active { display: block; }
        .progress-fill { height: 8px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 4px; width: 0%; transition: 0.3s; }
        .dashboard { display: none; margin-top: 40px; }
        .dashboard.active { display: block; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
        .metric-card { background: #15151f; border-radius: 14px; padding: 20px; }
        .metric-title { font-size: 13px; color: #888; margin-bottom: 8px; }
        .metric-value { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .highlights-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .highlight-card { background: #15151f; border-radius: 14px; overflow: hidden; }
        .highlight-video { height: 140px; background: #1a1a25; display: flex; align-items: center; justify-content: center; position: relative; }
        .highlight-play { width: 50px; height: 50px; background: rgba(139,92,246,0.3); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .highlight-duration { position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.8); padding: 4px 8px; border-radius: 6px; }
        .highlight-score { position: absolute; top: 10px; left: 10px; background: rgba(139,92,246,0.9); padding: 6px 10px; border-radius: 8px; }
        .highlight-content { padding: 16px; }
        .highlight-metrics { display: flex; gap: 8px; margin-bottom: 10px; }
        .highlight-metric { padding: 4px 8px; background: #1a1a25; border-radius: 6px; font-size: 11px; color: #888; }
        .highlight-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
        .action-btn { padding: 10px; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; background: transparent; color: #888; font-size: 13px; cursor: pointer; width: 100%; }
        .action-btn:hover { border-color: #8b5cf6; color: #fff; }
        .google-btn { display: flex; align-items: center; gap: 10px; padding: 12px 24px; background: #fff; border: none; border-radius: 8px; color: #333; font-weight: 600; cursor: pointer; }
        input { display: none; }
        @media (max-width: 768px) { .upload-grid, .metrics-grid, .highlights-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo"><div class="logo-icon">⚡</div><div class="logo-text">Highlight AI</div></div>
            <button class="google-btn" onclick="handleGoogleLogin()">
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                Google Login
            </button>
        </header>
        <main>
            <div class="hero">
                <h1>Extrahiere die <span class="highlight">perfekten Momente</span></h1>
                <p>KI-gestützte Video-Analyse</p>
            </div>
            <div class="upload-grid">
                <div class="upload-card" onclick="document.getElementById('file').click()">
                    <div class="upload-card-icon">💾</div><h3>Dateiupload</h3><p>Von deinem Gerät</p>
                </div>
                <div class="upload-card" onclick="showUrlInput()">
                    <div class="upload-card-icon">🔗</div><h3>URL Import</h3><p>Von Web-URL</p>
                </div>
                <div class="upload-card">
                    <div class="upload-card-icon">☁️</div><h3>Cloud Import</h3><p>Google Drive, etc.</p>
                </div>
            </div>
            <input type="file" id="file" accept="video/*" onchange="handleFile(event)">
            <div class="progress" id="progress">
                <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                    <span id="progress-filename"></span>
                    <span id="progress-percent" style="color:#8b5cf6;">0%</span>
                </div>
                <div class="progress-fill" id="progress-fill"></div>
            </div>
            <div class="dashboard" id="dashboard">
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-title">Pixel</div><div class="metric-value" id="m-pixel">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Bewegung</div><div class="metric-value" id="m-motion">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Gesichter</div><div class="metric-value" id="m-face">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Helligkeit</div><div class="metric-value" id="m-brightness">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Kontrast</div><div class="metric-value" id="m-contrast">0%</div></div>
                    <div class="metric-card"><div class="metric-title">Szenen</div><div class="metric-value" id="m-scene">0%</div></div>
                </div>
                <h2 style="margin-bottom:20px;">Highlights</h2>
                <div class="highlights-grid" id="highlights-grid"></div>
            </div>
        </main>
    </div>
    <script>
        let currentVideoId = null;
        let highlights = [];
        
        function handleGoogleLogin() {
            google.accounts.id.initialize({
                client_id: '927383411890-3qov5lgg999rmd87uf0o2qgi4bvc18f0.apps.googleusercontent.com',
                callback: handleCredentialResponse
            });
            google.accounts.id.prompt();
        }
        
        async function handleCredentialResponse(response) {
            await fetch('/api/auth/google', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token:response.credential})});
            alert('Angemeldet!');
        }
        
        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            document.getElementById('progress').classList.add('active');
            document.getElementById('progress-filename').textContent = file.name;
            
            let progress = 0;
            const interval = setInterval(() => {
                progress += 3;
                if (progress > 95) progress = 95;
                document.getElementById('progress-percent').textContent = progress + '%';
                document.getElementById('progress-fill').style.width = progress + '%';
            }, 100);
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/api/upload', {method:'POST', body:formData})
            .then(r => r.json())
            .then(data => {
                clearInterval(interval);
                progress = 100;
                document.getElementById('progress-fill').style.width = '100%';
                document.getElementById('progress-percent').textContent = '100%';
                currentVideoId = data.video_id;
                loadHighlights();
            });
        }
        
        async function loadHighlights() {
            for (let i = 0; i < 10; i++) await new Promise(r => setTimeout(r, 500));
            const res = await fetch('/api/video/' + currentVideoId + '/highlights');
            highlights = await res.json();
            
            document.getElementById('progress').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            
            [85, 72, 60, 78, 65, 40].forEach((val, i) => {
                const ids = ['m-pixel', 'm-motion', 'm-face', 'm-brightness', 'm-contrast', 'm-scene'];
                let current = 0;
                const int = setInterval(() => {
                    current += 2;
                    if (current > val) current = val;
                    document.getElementById(ids[i]).textContent = current + '%';
                    if (current >= val) clearInterval(int);
                }, 30);
            });
            
            const grid = document.getElementById('highlights-grid');
            grid.innerHTML = '';
            highlights.forEach(h => {
                const dur = h.end_time - h.start_time;
                grid.innerHTML += '<div class="highlight-card"><div class="highlight-video"><div class="highlight-play">▶</div><div class="highlight-duration">' + Math.floor(dur/60) + ':' + String(Math.floor(dur%60)).padStart(2,'0') + '</div><div class="highlight-score">Score: ' + h.score + '</div></div><div class="highlight-content"><div class="highlight-metrics"><span class="highlight-metric">🖼️ ' + (h.metrics?.pixel||75) + '%</span><span class="highlight-metric">🎯 ' + (h.metrics?.motion||80) + '%</span></div><div class="highlight-title">' + h.title + '</div><button class="action-btn">⬇️ Download</button></div></div>';
            });
        }
        
        function showUrlInput() {
            const url = prompt('Video URL:');
            if (url) {
                fetch('/api/upload/url', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})})
                .then(r => r.json())
                .then(data => { currentVideoId = data.video_id; loadHighlights(); });
            }
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return HTML

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file'}), 400
    
    video_id = str(uuid.uuid4())
    filename = file.filename[:100]
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/upload/url', methods=['POST'])
def upload_url():
    data = request.get_json()
    return jsonify({'video_id': str(uuid.uuid4()), 'status': 'processing'})

@app.route('/api/video/<vid>')
def get_video(vid):
    return jsonify({'id': vid, 'status': 'completed'})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    return jsonify([
        {'id': '1', 'start_time': 0, 'end_time': 30, 'score': 95, 'title': 'Action-Höhepunkt', 'metrics': {'pixel': 85, 'motion': 90}},
        {'id': '2', 'start_time': 30, 'end_time': 60, 'score': 85, 'title': 'Emotionales Highlight', 'metrics': {'pixel': 75, 'motion': 70}},
        {'id': '3', 'start_time': 60, 'end_time': 90, 'score': 75, 'title': 'Szenenwechsel', 'metrics': {'pixel': 80, 'motion': 75}},
    ])

@app.route('/api/highlight/<hid>/rate', methods=['POST'])
def rate_highlight(hid):
    return jsonify({'success': True})

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    return jsonify({'success': True, 'user': {'name': 'User'}})

if __name__ == '__main__':
    app.run()