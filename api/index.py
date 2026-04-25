from flask import Flask, jsonify, render_template_string, request, redirect
import os
import uuid
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024 * 1024  # 12GB

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

# HTML Template
HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://accounts.google.com/gsi/client" async defer></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0f; --card: #15151f; --purple: #8b5cf6; --lilac: #c084fc; --text: #fff; --muted: #888; }
        body { font-family: 'Outfit', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        header { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; font-weight: 700; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: var(--muted); font-size: 18px; }
        
        .upload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }
        .upload-card { background: var(--card); border: 2px dashed rgba(139,92,246,0.4); border-radius: 16px; padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-card:hover { border-color: var(--purple); transform: translateY(-5px); }
        .upload-card-icon { font-size: 40px; margin-bottom: 12px; }
        .upload-card h3 { font-size: 16px; margin-bottom: 8px; }
        .upload-card p { font-size: 13px; color: var(--muted); }
        
        .progress { display: none; margin-top: 30px; padding: 24px; background: var(--card); border-radius: 16px; }
        .progress.active { display: block; }
        .progress-bar { height: 8px; background: #1a1a25; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 4px; width: 0%; transition: width 0.3s; }
        
        .dashboard { display: none; margin-top: 40px; }
        .dashboard.active { display: block; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
        .metric-card { background: var(--card); border-radius: 14px; padding: 20px; border: 1px solid rgba(139,92,246,0.15); }
        .metric-title { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
        .metric-value { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .highlights-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .highlight-card { background: var(--card); border-radius: 14px; overflow: hidden; border: 1px solid rgba(139,92,246,0.15); }
        .highlight-video { height: 140px; background: #1a1a25; display: flex; align-items: center; justify-content: center; position: relative; }
        .highlight-play { width: 50px; height: 50px; background: rgba(139,92,246,0.3); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
        .highlight-duration { position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.8); padding: 4px 8px; border-radius: 6px; font-size: 12px; }
        .highlight-score { position: absolute; top: 10px; left: 10px; background: rgba(139,92,246,0.9); padding: 6px 10px; border-radius: 8px; font-size: 13px; font-weight: 600; }
        .highlight-content { padding: 16px; }
        .highlight-metrics { display: flex; gap: 8px; margin-bottom: 10px; }
        .highlight-metric { padding: 4px 8px; background: #1a1a25; border-radius: 6px; font-size: 11px; color: var(--muted); }
        .highlight-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
        .highlight-actions { display: flex; gap: 8px; }
        .action-btn { flex: 1; padding: 10px; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; background: transparent; color: var(--muted); font-size: 13px; cursor: pointer; }
        
        .rating-section { display: none; margin-top: 30px; padding: 24px; background: var(--card); border-radius: 14px; }
        .rating-section.active { display: block; }
        .rating-buttons { display: flex; gap: 12px; margin-bottom: 16px; }
        .rating-btn { flex: 1; padding: 14px; border: 2px solid rgba(139,92,246,0.3); border-radius: 10px; background: transparent; color: var(--muted); font-size: 15px; font-weight: 600; cursor: pointer; }
        .rating-btn.good:hover, .rating-btn.good.active { background: rgba(34,197,94,0.15); border-color: #22c55e; color: #22c55e; }
        .rating-btn.bad:hover, .rating-btn.bad.active { background: rgba(239,68,68,0.15); border-color: #ef4444; color: #ef4444; }
        
        .google-btn { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 12px 24px; background: #fff; border: none; border-radius: 8px; color: #333; font-weight: 600; cursor: pointer; font-size: 14px; }
        
        .user-info { display: flex; align-items: center; gap: 12px; }
        .user-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--purple); }
        .user-name { font-size: 14px; }
        
        input { display: none; }
        @media (max-width: 768px) { .upload-grid, .metrics-grid, .highlights-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo"><div class="logo-icon">⚡</div><div class="logo-text">Highlight AI</div></div>
            <div class="user-section" id="user-section">
                <button class="google-btn" onclick="handleGoogleLogin()">
                    <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                    Google Login
                </button>
            </div>
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
                    <span id="progress-percent" style="color:var(--purple);">0%</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
                <p style="margin-top:12px; font-size:13px; color:var(--muted);" id="progress-status">Wird hochgeladen...</p>
            </div>
            
            <div class="dashboard" id="dashboard">
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-title">🖼️ Pixel-Änderung</div><div class="metric-value" id="m-pixel">0%</div></div>
                    <div class="metric-card"><div class="metric-title">🎯 Bewegung</div><div class="metric-value" id="m-motion">0%</div></div>
                    <div class="metric-card"><div class="metric-title">👤 Gesichter</div><div class="metric-value" id="m-face">0%</div></div>
                    <div class="metric-card"><div class="metric-title">💡 Helligkeit</div><div class="metric-value" id="m-brightness">0%</div></div>
                    <div class="metric-card"><div class="metric-title">◐ Kontrast</div><div class="metric-value" id="m-contrast">0%</div></div>
                    <div class="metric-card"><div class="metric-title">🔄 Szenen</div><div class="metric-value" id="m-scene">0%</div></div>
                </div>
                
                <h2 style="margin-bottom:20px;">Highlights</h2>
                <div class="highlights-grid" id="highlights-grid"></div>
                
                <div class="rating-section" id="rating-section">
                    <h4 style="margin-bottom:16px;">Bewerte dieses Highlight</h4>
                    <div class="rating-buttons">
                        <button class="rating-btn good" onclick="setRating('good')">👍 Gut</button>
                        <button class="rating-btn bad" onclick="setRating('bad')">👎 Schlecht</button>
                    </div>
                    <textarea id="feedback" placeholder="Feedback (optional)" style="width:100%; padding:14px; background:#1a1a25; border:1px solid rgba(139,92,246,0.3); border-radius:10px; color:white; font-size:14px; min-height:80px;"></textarea>
                    <button onclick="submitRating()" style="margin-top:14px; padding:12px 24px; background:linear-gradient(135deg,#8b5cf6,#c084fc); border:none; border-radius:10px; color:white; font-weight:600; cursor:pointer;">Absenden</button>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        let currentVideoId = null;
        let highlights = [];
        let highlightIndex = 0;
        let user = null;
        
        // Google Login
        function handleGoogleLogin() {
            google.accounts.id.initialize({
                client_id: '927383411890-3qov5lgg999rmd87uf0o2qgi4bvc18f0.apps.googleusercontent.com',
                callback: handleCredentialResponse
            });
            google.accounts.id.prompt();
        }
        
        async function handleCredentialResponse(response) {
            try {
                const res = await fetch('/api/auth/google', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({token: response.credential})
                });
                const data = await res.json();
                if (data.success) {
                    user = data.user;
                    updateUserUI();
                }
            } catch(e) {
                console.error(e);
            }
        }
        
        function updateUserUI() {
            if (user) {
                document.getElementById('user-section').innerHTML = 
                    '<div class="user-info"><div class="user-avatar" style="background:url(' + user.picture + ') no-repeat; background-size:cover;"></div><span class="user-name">' + user.name + '</span></div>';
            }
        }
        
        // File Upload
        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            document.getElementById('progress').classList.add('active');
            document.getElementById('progress-filename').textContent = file.name;
            
            const formData = new FormData();
            formData.append('file', file);
            
            let progress = 0;
            const progressInt = setInterval(() => {
                progress += 5;
                if (progress > 90) progress = 90;
                document.getElementById('progress-percent').textContent = progress + '%';
                document.getElementById('progress-fill').style.width = progress + '%';
            }, 200);
            
            fetch('/api/upload', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                clearInterval(progressInt);
                progress = 100;
                document.getElementById('progress-percent').textContent = '100%';
                document.getElementById('progress-fill').style.width = '100%';
                document.getElementById('progress-status').textContent = 'Wird analysiert...';
                
                currentVideoId = data.video_id;
                loadHighlights();
            })
            .catch(err => {
                clearInterval(progressInt);
                alert('Fehler: ' + err.message);
            });
        }
        
        async function loadHighlights() {
            // Poll for completion
            for (let i = 0; i < 30; i++) {
                await new Promise(r => setTimeout(r, 1000));
                const res = await fetch('/api/video/' + currentVideoId);
                const data = await res.json();
                if (data.status === 'completed' || data.status === 'uploaded') break;
            }
            
            const res = await fetch('/api/video/' + currentVideoId + '/highlights');
            highlights = await res.json();
            
            document.getElementById('progress').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            
            // Animate metrics
            [85, 72, 60, 78, 65, 40].forEach((val, i) => {
                const ids = ['m-pixel', 'm-motion', 'm-face', 'm-brightness', 'm-contrast', 'm-scene'];
                animateMetric(ids[i], val);
            });
            
            renderHighlights();
        }
        
        function animateMetric(id, target) {
            let current = 0;
            const el = document.getElementById(id);
            const int = setInterval(() => {
                current += 2;
                if (current > target) current = target;
                el.textContent = current + '%';
                if (current >= target) clearInterval(int);
            }, 30);
        }
        
        function renderHighlights() {
            const grid = document.getElementById('highlights-grid');
            grid.innerHTML = '';
            
            highlights.forEach((h, i) => {
                const dur = h.end_time - h.start_time;
                const mins = Math.floor(dur / 60);
                const secs = Math.floor(dur % 60);
                grid.innerHTML += `
                    <div class="highlight-card" onclick="showRating(${i})">
                        <div class="highlight-video">
                            <div class="highlight-play">▶</div>
                            <div class="highlight-duration">${mins}:${String(secs).padStart(2, '0')}</div>
                            <div class="highlight-score">Score: ${h.score}</div>
                        </div>
                        <div class="highlight-content">
                            <div class="highlight-metrics">
                                <span class="highlight-metric">🖼️ ${h.metrics?.pixel || 75}%</span>
                                <span class="highlight-metric">🎯 ${h.metrics?.motion || 80}%</span>
                            </div>
                            <div class="highlight-title">${h.title}</div>
                            <div class="highlight-actions">
                                <button class="action-btn">⬇️ Download</button>
                                <button class="action-btn">📱 Export</button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        
        function showRating(i) {
            highlightIndex = i;
            document.getElementById('rating-section').classList.add('active');
            document.getElementById('rating-section').scrollIntoView({behavior: 'smooth'});
        }
        
        function setRating(r) {
            document.querySelectorAll('.rating-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.rating-btn.' + r).classList.add('active');
        }
        
        async function submitRating() {
            const rating = document.querySelector('.rating-btn.active')?.classList.contains('good') ? 'good' : 'bad';
            const feedback = document.getElementById('feedback').value;
            
            try {
                await fetch('/api/highlight/' + highlights[highlightIndex].id + '/rate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({rating, feedback})
                });
            } catch(e) {}
            
            alert('Danke für Feedback!');
            document.getElementById('rating-section').classList.remove('active');
            if (highlightIndex < highlights.length - 1) showRating(highlightIndex + 1);
        }
        
        function showUrlInput() {
            const url = prompt('Video URL:');
            if (url) {
                fetch('/api/upload/url', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url})
                })
                .then(r => r.json())
                .then(data => {
                    currentVideoId = data.video_id;
                    loadHighlights();
                });
            }
        }
    </script>
</body>
</html>
'''

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, filename TEXT, original_path TEXT, upload_time TEXT, file_size INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS highlights (
        id TEXT PRIMARY KEY, video_id TEXT, start_time REAL, end_time REAL, score REAL,
        title TEXT, description TEXT, metrics TEXT, rating TEXT, feedback TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, email TEXT, name TEXT, picture TEXT, google_token TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return HTML

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    video_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    os.makedirs('uploads', exist_ok=True)
    path = f'uploads/{video_id}_{filename}'
    file.save(path)
    
    file_size = os.path.getsize(path)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?)',
             (video_id, filename, path, datetime.now().isoformat(), file_size, 'processing'))
    
    # Create simulated highlights and metrics
    types = [
        ('Action-Höhepunkt', 'Hochintensive Bewegung', {'pixel': 85, 'motion': 90}),
        ('Emotionales Highlight', 'Hochintensive Emotionen', {'pixel': 75, 'motion': 65}),
        ('Szenenwechsel', 'Dynamischer Szenenwechsel', {'pixel': 80, 'motion': 75}),
        ('Highlight', 'Besonderer Moment', {'pixel': 70, 'motion': 60}),
    ]
    
    for i, (title, desc, metrics) in enumerate(types):
        c.execute('INSERT INTO highlights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (str(uuid.uuid4()), video_id, i*20, (i+1)*20, 100-i*15, title, desc, str(metrics), None, None))
    
    conn.commit()
    conn.close()
    
    # Simulate processing delay
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/upload/url', methods=['POST'])
def upload_url():
    data = request.get_json()
    url = data.get('url', '')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    
    import urllib.request
    video_id = str(uuid.uuid4())
    filename = secure_filename(url.split('/')[-1].split('?')[0]) or 'video.mp4'
    
    os.makedirs('uploads', exist_ok=True)
    path = f'uploads/{video_id}_{filename}'
    
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?)',
             (video_id, filename, path, datetime.now().isoformat(), os.path.getsize(path), 'processing'))
    
    for i, (title, desc, metrics) in enumerate([('Action', 'Action', {'pixel':85,'motion':90}), ('Highlight', 'Highlight', {'pixel':75,'motion':70})]):
        c.execute('INSERT INTO highlights VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                 (str(uuid.uuid4()), video_id, i*30, (i+1)*30, 95-i*10, title, desc, str(metrics), None, None))
    
    conn.commit()
    conn.close()
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/video/<vid>')
def get_video(vid):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (vid,))
    v = c.fetchone()
    conn.close()
    if not v:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': v[0], 'filename': v[1], 'status': v[5], 'file_size': v[4]})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM highlights WHERE video_id = ?', (vid,))
    h = c.fetchall()
    conn.close()
    return jsonify([
        {'id': x[0], 'start_time': x[2], 'end_time': x[3], 'score': x[4], 'title': x[5], 
         'description': x[6], 'metrics': eval(x[7]) if x[7] else {}, 'rating': x[8], 'feedback': x[9]}
        for x in h
    ])

@app.route('/api/highlight/<hid>/rate', methods=['POST'])
def rate_highlight(hid):
    data = request.get_json()
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE highlights SET rating = ?, feedback = ? WHERE id = ?',
             (data.get('rating'), data.get('feedback', ''), hid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json()
    token = data.get('token', '')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    try:
        if GOOGLE_CLIENT_ID:
            from google.oauth2 import id_token
            from google.auth.transport import requests as gr
            id_info = id_token.verify_token(token, gr.Request(), GOOGLE_CLIENT_ID)
        else:
            id_info = {'sub': str(uuid.uuid4()), 'email': 'demo@test.com', 'name': 'Demo User', 'picture': ''}
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)',
                 (id_info['sub'], id_info.get('email', ''), id_info.get('name', ''), id_info.get('picture', ''), token, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'user': {'id': id_info['sub'], 'email': id_info.get('email', ''), 'name': id_info.get('name', ''), 'picture': id_info.get('picture', '')}})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})