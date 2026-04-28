from flask import Flask, jsonify, request
import uuid
from datetime import datetime, timedelta
import random
import string
import os
import requests
import hmac
import hashlib
import json

app = Flask(__name__)

RESEND_KEY = os.environ.get('RESEND_API_KEY', 're_6rbaVj9Q_HsW3ohbAPUGtBjv5wL9LtT1w')
SECRET_KEY = os.environ.get('SECRET_KEY', 'highlight-ai-secret-2026')

sessions_db = {}
videos_db = {}

def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def create_verify_token(email, code):
    data = json.dumps({'email': email, 'code': code, 'exp': datetime.now().timestamp() + 300})
    signature = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
    return data + '.' + signature

def verify_token(token):
    try:
        data, signature = token.rsplit('.', 1)
        expected = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()
        if signature != expected:
            return None
        info = json.loads(data)
        if datetime.now().timestamp() > info['exp']:
            return None
        return info
    except:
        return None

def send_verification_email(email, code):
    try:
        r = requests.post('https://api.resend.com/emails', {
            'from': 'Highlight AI <onboarding@resend.dev>',
            'to': email,
            'subject': '🔐 Dein Bestätigungscode für Highlight AI',
            'html': f'''
            <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto; padding: 20px; background: #0a0a0f; color: #fff;">
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
        .history-section { margin-top: 60px; }
        .history-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
        .history-card { background: #15151f; border-radius: 14px; padding: 16px; cursor: pointer; }
        .history-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
        .history-date { font-size: 12px; color: #888; }
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
                    <div class="upload-card" id="upload-file">
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
        var user = null;
        var currentVideoId = null;
        var verifyToken = null;
        
        document.getElementById('verify-btn').addEventListener('click', verifyCode);
        document.getElementById('upload-file').addEventListener('click', function() { document.getElementById('file').click(); });
        document.getElementById('file').addEventListener('change', handleFile);
        document.getElementById('upload-url').addEventListener('click', showUrlInput);
        
        function sendCode() {
            var email = document.getElementById('email-input').value;
            if (!email || email.indexOf('@') === -1) { alert('Bitte E-Mail eingeben'); return; }
            
            var btn = document.getElementById('send-btn');
            btn.disabled = true;
            btn.textContent = 'Wird gesendet...';
            
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/auth/send-code', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        verifyToken = data.verify_token;
                        document.getElementById('otp-section').style.display = 'block';
                        btn.textContent = 'Code gesendet!';
                        alert('Dein Code ist: ' + data.code + '\n(Der Code wurde auch per E-Mail gesendet)');
                    } else {
                        alert('Fehler: ' + data.error);
                        btn.disabled = false;
                        btn.textContent = 'Code senden';
                    }
                } else {
                    alert('Fehler beim Senden');
                    btn.disabled = false;
                    btn.textContent = 'Code senden';
                }
            };
            xhr.send(JSON.stringify({email: email}));
        }
        
        function verifyCode() {
            var email = document.getElementById('email-input').value;
            var code = document.getElementById('otp-input').value;
            
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/auth/verify', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    if (data.success) {
                        localStorage.setItem('highlight_token', data.token);
                        user = data.user;
                        showLoggedIn();
                    } else {
                        alert('Falscher Code oder abgelaufen!');
                    }
                } else {
                    alert('Fehler bei der Verifizierung');
                }
            };
            xhr.send(JSON.stringify({email: email, code: code, verify_token: verifyToken}));
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
        
        function loadHistory() {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/history/' + user.email, true);
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var videos = JSON.parse(xhr.responseText);
                    var grid = document.getElementById('history-grid');
                    if (videos.length === 0) {
                        grid.innerHTML = '<p style="color:#888;">Noch keine Videos</p>';
                    } else {
                        var html = '';
                        for (var i = 0; i < videos.length; i++) {
                            var card = document.createElement('div');
                            card.className = 'history-card';
                            card.dataset.id = videos[i].id;
                            card.onclick = function() { loadVideo(this.dataset.id); };
                            card.innerHTML = '<div class="history-title">' + videos[i].filename + '</div><div class="history-date">' + videos[i].date + '</div>';
                            grid.appendChild(card);
                        }
                    }
                }
            };
            xhr.send();
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
            formData.append('token', localStorage.getItem('highlight_token'));
            
            var xhr = new XMLHttpRequest();
            xhr.upload.onprogress = function(evt) {
                if (evt.lengthComputable) {
                    var percent = Math.round((evt.loaded / evt.total) * 100);
                    document.getElementById('progress-percent').textContent = percent + '%';
                    document.getElementById('progress-fill').style.width = percent + '%';
                }
            };
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    currentVideoId = data.video_id;
                    loadHighlights(currentVideoId);
                    loadHistory();
                }
            };
            xhr.open('POST', '/api/upload', true);
            xhr.send(formData);
        }
        
        function loadHighlights(vid) {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/api/video/' + vid + '/highlights', true);
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var highlights = JSON.parse(xhr.responseText);
                    document.getElementById('dashboard').classList.add('active');
                    
                    var metrics = [85, 72, 60, 78, 65, 40];
                    var ids = ['m-pixel', 'm-motion', 'm-face', 'm-brightness', 'm-contrast', 'm-scene'];
                    for (var i = 0; i < 6; i++) {
                        (function(idx) {
                            var current = 0;
                            var timer = setInterval(function() {
                                current += 2;
                                if (current > metrics[idx]) current = metrics[idx];
                                document.getElementById(ids[idx]).textContent = current + '%';
                                if (current >= metrics[idx]) clearInterval(timer);
                            }, 30);
                        })(i);
                    }
                    
                    var grid = document.getElementById('highlights-grid');
                    var html = '';
                    for (var j = 0; j < highlights.length; j++) {
                        var h = highlights[j];
                        var dur = h.end_time - h.start_time;
                        var min = Math.floor(dur / 60);
                        var sec = Math.floor(dur % 60);
                        html += '<div class="highlight-card"><div class="highlight-video"><div style="font-size:40px;">▶</div><div class="highlight-duration">' + min + ':' + (sec < 10 ? '0' : '') + sec + '</div><div class="highlight-score">Score: ' + h.score + '</div></div><div class="highlight-content"><div class="highlight-title">' + h.title + '</div></div></div>';
                    }
                    grid.innerHTML = html;
                }
            };
            xhr.send();
        }
        
        function showUrlInput() {
            var url = prompt('Video URL:');
            if (url) {
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/upload/url', true);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var data = JSON.parse(xhr.responseText);
                        currentVideoId = data.video_id;
                        loadHighlights(data.video_id);
                    }
                };
                xhr.send(JSON.stringify({url: url, email: user.email, token: localStorage.getItem('highlight_token')}));
            }
        }
        
        var token = localStorage.getItem('highlight_token');
        if (token) {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/auth/check', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    if (data.success) { user = data.user; showLoggedIn(); }
                }
            };
            xhr.send(JSON.stringify({token: token}));
        }
    </script>
</body>
</html>'''

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
    verify_token = create_verify_token(email, code)
    
    send_verification_email(email, code)
    
    return jsonify({'success': True, 'verify_token': verify_token, 'code': code, 'message': 'Code wurde per E-Mail gesendet'})

@app.route('/api/auth/verify', methods=['POST'])
def verify_code():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    code = data.get('code', '')
    verify_token = data.get('verify_token', '')
    
    info = verify_token(verify_token)
    if not info:
        return jsonify({'error': 'Ungültiger Token'}), 400
    
    if info['email'] != email or info['code'] != code:
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
    filename = request.files['file'].filename[:100] if request.files['file'].filename else 'video.mp4'
    
    videos_db[video_id] = {'email': email, 'filename': filename, 'date': datetime.now().isoformat(), 'status': 'uploaded'}
    
    return jsonify({'video_id': video_id, 'status': 'uploaded'})

@app.route('/api/upload/url', methods=['POST'])
def upload_url():
    data = request.get_json()
    url = data.get('url', '')
    email = data.get('email', '')
    token = data.get('token', '')
    
    if not email or not token:
        return jsonify({'error': 'Not logged in'}), 401
    
    video_id = str(uuid.uuid4())
    videos_db[video_id] = {'email': email, 'filename': url.split('/')[-1][:100], 'date': datetime.now().isoformat(), 'status': 'uploaded'}
    
    return jsonify({'video_id': video_id, 'status': 'uploaded'})

@app.route('/api/video/<vid>')
def get_video(vid):
    if vid not in videos_db:
        return jsonify({'error': 'Not found'}), 404
    v = videos_db[vid]
    return jsonify({'id': vid, 'filename': v['filename'], 'status': v['status']})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    return jsonify([
        {'id': '1', 'start_time': 0, 'end_time': 30, 'score': 95, 'title': 'Action-Höhepunkt'},
        {'id': '2', 'start_time': 30, 'end_time': 60, 'score': 85, 'title': 'Emotionales Highlight'},
        {'id': '3', 'start_time': 60, 'end_time': 90, 'score': 75, 'title': 'Szenenwechsel'},
    ])

@app.route('/api/history/<email>')
def history(email):
    email = email.lower()
    videos = [{'id': vid, 'filename': v['filename'], 'date': v['date'][:10], 'status': v['status']} 
             for vid, v in videos_db.items() if v.get('email') == email]
    return jsonify(videos)

if __name__ == '__main__':
    app.run(debug=True)