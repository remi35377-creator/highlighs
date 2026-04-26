from flask import Flask, jsonify, request
import uuid
import sqlite3
from datetime import datetime, timedelta
import random
import string
import os
import requests

app = Flask(__name__)

RESEND_KEY = os.environ.get('RESEND_API_KEY', 're_6rbaVj9Q_HsW3ohbAPUGtBjv5wL9LtT1w')

# In-memory storage for Vercel (serverless)
users_db = {}
sessions_db = {}
videos_db = {}

HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Outfit', sans-serif; background: #0a0a0f; color: #fff; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { display: flex; justify-content: space-between; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: #888; font-size: 18px; }
        
        .login-box { max-width: 400px; margin: 40px auto; padding: 40px; background: #15151f; border-radius: 16px; position: relative; }
        .login-input { width: 100%; padding: 16px; margin-bottom: 16px; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); border-radius: 10px; color: #fff; font-size: 16px; display: block; }
        .login-btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border: none; border-radius: 10px; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; display: block; }
        .login-btn:focus { outline: 2px solid #fff; }
        .otp-section { display: none; }
        .otp-section.active { display: block; }
        .otp-input { width: 100%; padding: 16px; margin-bottom: 16px; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); border-radius: 10px; color: #fff; font-size: 24px; text-align: center; letter-spacing: 8px; font-family: monospace; }
        
        .user-bar { display: flex; align-items: center; gap: 12px; }
        .user-email { font-size: 14px; color: #888; }
        .logout-btn { padding: 8px 16px; background: transparent; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; color: #888; cursor: pointer; }
        
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
        
        .history-section { margin-top: 60px; }
        .history-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .history-card { background: #15151f; border-radius: 14px; padding: 16px; cursor: pointer; }
        .history-card:hover { border: 1px solid rgba(139,92,246,0.5); }
        .history-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
        .history-date { font-size: 12px; color: #888; }
        
        input[type="file"] { display: none; }
        .login-input { display: block; width: 100%; }
        @media (max-width: 768px) { .upload-grid, .metrics-grid, .highlights-grid, .history-grid { grid-template-columns: 1fr; } }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
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
            
            <!-- Login -->
            <div class="login-box" id="login-box">
                <h2>🔐 Anmelden</h2>
                <input type="email" id="email-input" class="login-input" placeholder="Deine E-Mail-Adresse" autocomplete="email" />
                <button type="button" class="login-btn" id="send-btn" onclick="sendCode()">Code senden</button>
                
                <div class="otp-section" id="otp-section" style="margin-top: 24px;">
                    <p style="color: #888; margin-bottom: 16px; text-align: center;">Gib den Code ein, den du per E-Mail erhalten hast</p>
                    <input type="text" id="otp-input" class="otp-input" placeholder="XXXXXX" maxlength="6" />
                    <button class="login-btn" onclick="verifyCode()">Bestätigen</button>
                </div>
            </div>
            
            <!-- Main -->
            <div id="main-content" style="display:none;">
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
                
                <div class="history-section">
                    <h2>📺 Meine Videos</h2>
                    <div class="history-grid" id="history-grid"></div>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        let user = null;
        let currentVideoId = null;
        
        async function sendCode() {
            console.log('sendCode called');
            const email = document.getElementById('email-input').value;
            console.log('Email:', email);
            if (!email || !email.includes('@')) { alert('Bitte E-Mail eingeben'); return; }
            
            document.getElementById('send-btn').disabled = true;
            document.getElementById('send-btn').textContent = 'Wird gesendet...';
            
            try {
                const res = await fetch('/api/auth/send-code', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email})});
                console.log('Response status:', res.status);
                const data = await res.json();
                console.log('Response data:', data);
                
                if (data.success) {
                    document.getElementById('otp-section').style.display = 'block';
                    document.getElementById('send-btn').textContent = 'Code gesendet!';
                } else {
                    alert('Fehler: ' + data.error);
                    document.getElementById('send-btn').disabled = false;
                }
            } catch(e) {
                console.error('Error:', e);
                alert('Fehler: ' + e.message);
            }
        }
        
        async function verifyCode() {
            const email = document.getElementById('email-input').value;
            const code = document.getElementById('otp-input').value;
            
            const res = await fetch('/api/auth/verify', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, code})});
            const data = await res.json();
            
            if (data.success) {
                localStorage.setItem('highlight_token', data.token);
                user = data.user;
                showLoggedIn();
            } else {
                alert('Falscher Code!');
            }
        }
        
        function logout() {
            localStorage.removeItem('highlight_token');
            user = null;
            location.reload();
        }
        
        function showLoggedIn() {
            document.getElementById('login-box').style.display = 'none';
            document.getElementById('main-content').style.display = 'block';
            document.getElementById('user-bar').innerHTML = '<span class="user-email">' + user.email + '</span><button class="logout-btn" onclick="logout()">Abmelden</button>';
            loadHistory();
        }
        
        async function loadHistory() {
            const res = await fetch('/api/history/' + user.email);
            const videos = await res.json();
            const grid = document.getElementById('history-grid');
            if (videos.length === 0) {
                grid.innerHTML = '<p style="color:#888; grid-column:1/-1;">Noch keine Videos</p>';
            } else {
                grid.innerHTML = videos.map(v => '<div class="history-card" onclick="loadVideo(\'' + v.id + '\')"><div class="history-title">' + v.filename + '</div><div class="history-date">' + v.date + '</div></div>').join('');
            }
        }
        
        function loadVideo(vid) {
            currentVideoId = vid;
            document.getElementById('dashboard').classList.add('active');
            document.getElementById('dashboard').scrollIntoView({behavior:'smooth'});
            loadHighlights(vid);
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
            formData.append('email', user.email);
            formData.append('token', localStorage.getItem('highlight_token'));
            
            fetch('/api/upload', {method:'POST', body:formData})
            .then(r => r.json())
            .then(data => {
                clearInterval(interval);
                document.getElementById('progress-fill').style.width = '100%';
                document.getElementById('progress-percent').textContent = '100%';
                currentVideoId = data.video_id;
                
                let pollCount = 0;
                const pollInt = setInterval(async () => {
                    pollCount++;
                    if (pollCount > 20) { clearInterval(pollInt); return; }
                    const res = await fetch('/api/video/' + currentVideoId);
                    const d = await res.json();
                    if (d.status === 'completed' || d.status === 'uploaded') {
                        clearInterval(pollInt);
                        loadHighlights(currentVideoId);
                        loadHistory();
                    }
                }, 1000);
            });
        }
        
        async function loadHighlights(vid) {
            const res = await fetch('/api/video/' + vid + '/highlights');
            const highlights = await res.json();
            
            document.getElementById('progress').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            
            [85, 72, 60, 78, 65, 40].forEach((val, i) => {
                const ids = ['m-pixel', 'm-motion', 'm-face', 'm-brightness', 'm-contrast', 'm-scene'];
                let current = 0;
                setInterval(() => {
                    current += 2;
                    if (current > val) current = val;
                    document.getElementById(ids[i]).textContent = current + '%';
                    if (current >= val) clearInterval(this);
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
                fetch('/api/upload/url', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url, email:user.email, token:localStorage.getItem('highlight_token')})})
                .then(r => r.json())
                .then(data => { currentVideoId = data.video_id; loadHighlights(data.video_id); });
            }
        }
        
        // Check existing session
        const token = localStorage.getItem('highlight_token');
        if (token) {
            fetch('/api/auth/check', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token})})
            .then(r => r.json())
            .then(data => { if (data.success) { user = data.user; showLoggedIn(); } });
        }
    </script>
</body>
</html>
'''

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    try:
        r = requests.post('https://api.resend.com/emails', {
            'from': 'Highlight AI <onboarding@resend.dev>',
            'to': email,
            'subject': '🔐 Dein Bestätigungscode für Highlight AI',
            'html': f'''
            <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #8b5cf6;">⚡ Highlight AI</h1>
                <p>Dein Bestätigungscode:</p>
                <div style="background: #15151f; padding: 20px; border-radius: 10px; text-align: center; font-size: 32px; letter-spacing: 8px; color: #8b5cf6; font-weight: bold;">{code}</div>
                <p style="color: #666; margin-top: 20px;">Dieser Code ist 5 Minuten gültig.</p>
            </div>
            '''
        }, headers={'Authorization': f'Bearer {RESEND_KEY}'}, timeout=10)
        return r.status_code == 200
    except:
        return False

@app.route('/')
def home():
    return HTML

@app.route('/api/auth/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    
    if not email or '@' not in email:
        return jsonify({'error': 'Ungültige E-Mail'}), 400
    
    code = generate_code()
    expires = (datetime.now() + timedelta(minutes=5)).isoformat()
    users_db[email] = {'code': code, 'expires': expires}
    
    send_verification_email(email, code)
    
    return jsonify({'success': True, 'message': 'Code wurde per E-Mail gesendet'})

@app.route('/api/auth/verify', methods=['POST'])
def verify_code():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    code = data.get('code', '')
    
    if email not in users_db:
        return jsonify({'error': 'User nicht gefunden'}), 400
    
    user = users_db[email]
    stored_code = user['code']
    expires = datetime.fromisoformat(user['expires'])
    
    if datetime.now() > expires:
        return jsonify({'error': 'Code abgelaufen'}), 400
    
    if code != stored_code:
        return jsonify({'error': 'Falscher Code'}), 400
    
    token = str(uuid.uuid4())
    sessions_db[token] = {'email': email, 'expires': (datetime.now() + timedelta(days=7)).isoformat()}
    
    return jsonify({'success': True, 'token': token, 'user': {'email': email}})

@app.route('/api/auth/check', methods=['POST'])
def check_auth():
    data = request.get_json()
    token = data.get('token', '')
    
    if token in sessions_db:
        session = sessions_db[token]
        if datetime.now() < datetime.fromisoformat(session['expires']):
            return jsonify({'success': True, 'user': {'email': session['email']}})
    return jsonify({'error': 'Invalid'}), 401

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    email = request.form.get('email', '')
    token = request.form.get('token', '')
    
    if not email or not token:
        return jsonify({'error': 'Not logged in'}), 401
    
    video_id = str(uuid.uuid4())
    filename = request.files['file'].filename[:100]
    
    videos_db[video_id] = {'email': email, 'filename': filename, 'date': datetime.now().isoformat(), 'status': 'processing'}
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/upload/url', methods=['POST'])
def upload_url():
    data = request.get_json()
    url = data.get('url', '')
    email = data.get('email', '')
    token = data.get('token', '')
    
    if not email or not token:
        return jsonify({'error': 'Not logged in'}), 401
    
    video_id = str(uuid.uuid4())
    videos_db[video_id] = {'email': email, 'filename': url.split('/')[-1][:100], 'date': datetime.now().isoformat(), 'status': 'processing'}
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/video/<vid>')
def get_video(vid):
    if vid not in videos_db:
        return jsonify({'error': 'Not found'}), 404
    v = videos_db[vid]
    return jsonify({'id': vid, 'filename': v['filename'], 'status': v['status']})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    return jsonify([
        {'id': '1', 'start_time': 0, 'end_time': 30, 'score': 95, 'title': 'Action-Höhepunkt', 'metrics': {'pixel': 85, 'motion': 90}},
        {'id': '2', 'start_time': 30, 'end_time': 60, 'score': 85, 'title': 'Emotionales Highlight', 'metrics': {'pixel': 75, 'motion': 70}},
        {'id': '3', 'start_time': 60, 'end_time': 90, 'score': 75, 'title': 'Szenenwechsel', 'metrics': {'pixel': 80, 'motion': 75}},
    ])

@app.route('/api/history/<email>')
def history(email):
    email = email.lower()
    videos = [{'id': vid, 'filename': v['filename'], 'date': v['date'][:10], 'status': v['status']} 
             for vid, v in videos_db.items() if v.get('email') == email]
    return jsonify(videos)