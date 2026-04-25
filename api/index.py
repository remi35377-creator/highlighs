from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI - Video Intelligence</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-primary: #0a0a0f;
            --bg-card: #15151f;
            --accent-purple: #8b5cf6;
            --accent-lilac: #c084fc;
            --text-primary: #ffffff;
            --text-secondary: #a1a1aa;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        /* Header */
        header { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 1px solid rgba(139,92,246,0.15); }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 44px; height: 44px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; }
        .logo-text { font-size: 22px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        /* Hero */
        .hero { text-align: center; padding: 60px 0; }
        .hero h1 { font-size: 48px; font-weight: 700; margin-bottom: 16px; }
        .hero h1 .highlight { background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { color: var(--text-secondary); font-size: 18px; }
        
        /* Upload Cards */
        .upload-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 40px; }
        .upload-card {
            background: var(--bg-card);
            border: 2px dashed rgba(139,92,246,0.4);
            border-radius: 16px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-card:hover { border-color: var(--accent-purple); transform: translateY(-5px); }
        .upload-card-icon { font-size: 40px; margin-bottom: 12px; }
        .upload-card h3 { font-size: 16px; margin-bottom: 8px; }
        .upload-card p { font-size: 13px; color: var(--text-secondary); }
        
        /* Progress */
        .progress-section { display: none; margin-top: 30px; padding: 24px; background: var(--bg-card); border-radius: 16px; }
        .progress-section.active { display: block; }
        .progress-bar { height: 8px; background: #1a1a25; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(135deg, #8b5cf6, #c084fc); border-radius: 4px; width: 0%; transition: width 0.3s; }
        
        /* Dashboard */
        .dashboard { display: none; margin-top: 40px; }
        .dashboard.active { display: block; }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 40px; }
        .metric-card { background: var(--bg-card); border-radius: 14px; padding: 20px; border: 1px solid rgba(139,92,246,0.15); }
        .metric-title { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
        .metric-value { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        /* Highlights */
        .highlights-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .highlight-card { background: var(--bg-card); border-radius: 14px; overflow: hidden; border: 1px solid rgba(139,92,246,0.15); }
        .highlight-video { height: 140px; background: #1a1a25; display: flex; align-items: center; justify-content: center; }
        .highlight-play { width: 50px; height: 50px; background: rgba(139,92,246,0.3); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .highlight-duration { position: absolute; bottom: 10px; right: 10px; padding: 4px 8px; background: rgba(0,0,0,0.8); border-radius: 6px; font-size: 12px; }
        .highlight-score { position: absolute; top: 10px; left: 10px; padding: 6px 10px; background: rgba(139,92,246,0.9); border-radius: 8px; font-size: 13px; font-weight: 600; }
        .highlight-content { padding: 16px; }
        .highlight-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
        .highlight-metrics { display: flex; gap: 8px; margin-bottom: 10px; }
        .highlight-metric { padding: 4px 8px; background: #1a1a25; border-radius: 6px; font-size: 11px; color: var(--text-secondary); }
        .highlight-actions { display: flex; gap: 8px; }
        .action-btn { flex: 1; padding: 10px; border: 1px solid rgba(139,92,246,0.3); border-radius: 8px; background: transparent; color: var(--text-secondary); font-size: 13px; cursor: pointer; }
        .action-btn:hover { border-color: var(--accent-purple); color: var(--text-primary); }
        
        /* Rating */
        .rating-section { display: none; margin-top: 30px; padding: 24px; background: var(--bg-card); border-radius: 14px; }
        .rating-section.active { display: block; }
        .rating-buttons { display: flex; gap: 12px; margin-bottom: 16px; }
        .rating-btn { flex: 1; padding: 14px; border: 2px solid rgba(139,92,246,0.3); border-radius: 10px; background: transparent; color: var(--text-secondary); font-size: 15px; font-weight: 600; cursor: pointer; }
        .rating-btn.good:hover, .rating-btn.good.active { background: rgba(34,197,94,0.15); border-color: #22c55e; color: #22c55e; }
        .rating-btn.bad:hover, .rating-btn.bad.active { background: rgba(239,68,68,0.15); border-color: #ef4444; color: #ef4444; }
        
        input { display: none; }
        @media (max-width: 768px) { .upload-grid, .metrics-grid, .highlights-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">⚡</div>
                <div class="logo-text">Highlight AI</div>
            </div>
        </header>
        
        <main>
            <div class="hero">
                <h1>Extrahiere die <span class="highlight">perfekten Momente</span></h1>
                <p>KI-gestützte Video-Analyse</p>
            </div>
            
            <div class="upload-grid">
                <div class="upload-card" onclick="document.getElementById('file').click()">
                    <div class="upload-card-icon">💾</div>
                    <h3>Dateiupload</h3>
                    <p>Von deinem Gerät</p>
                </div>
                <div class="upload-card" onclick="showUrlInput()">
                    <div class="upload-card-icon">🔗</div>
                    <h3>URL Import</h3>
                    <p>Von Web-URL</p>
                </div>
                <div class="upload-card">
                    <div class="upload-card-icon">☁️</div>
                    <h3>Cloud Import</h3>
                    <p>Google Drive, etc.</p>
                </div>
            </div>
            
            <input type="file" id="file" accept="video/*" onchange="handleFile(event)">
            
            <div class="progress-section" id="progress">
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span id="progress-filename"></span>
                    <span id="progress-percent" style="color: var(--accent-purple);">0%</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
                <p style="margin-top: 12px; font-size: 13px; color: var(--text-secondary);" id="progress-status">Wird hochgeladen...</p>
            </div>
            
            <div class="dashboard" id="dashboard">
                <div class="metrics-grid">
                    <div class="metric-card"><div class="metric-title">🖼️ Pixel-Änderung</div><div class="metric-value" id="metric-pixel">0%</div></div>
                    <div class="metric-card"><div class="metric-title">🎯 Bewegung</div><div class="metric-value" id="metric-motion">0%</div></div>
                    <div class="metric-card"><div class="metric-title">👤 Gesichter</div><div class="metric-value" id="metric-face">0%</div></div>
                    <div class="metric-card"><div class="metric-title">💡 Helligkeit</div><div class="metric-value" id="metric-brightness">0%</div></div>
                    <div class="metric-card"><div class="metric-title">◐ Kontrast</div><div class="metric-value" id="metric-contrast">0%</div></div>
                    <div class="metric-card"><div class="metric-title">🔄 Szenen</div><div class="metric-value" id="metric-scene">0%</div></div>
                </div>
                
                <h2 style="margin-bottom: 20px;">Highlights</h2>
                <div class="highlights-grid" id="highlights-grid"></div>
                
                <div class="rating-section" id="rating-section">
                    <h4 style="margin-bottom: 16px;">Bewerte dieses Highlight</h4>
                    <div class="rating-buttons">
                        <button class="rating-btn good" onclick="setRating('good')">👍 Gut</button>
                        <button class="rating-btn bad" onclick="setRating('bad')">👎 Schlecht</button>
                    </div>
                    <textarea id="feedback" placeholder="Feedback (optional)" style="width: 100%; padding: 14px; background: #1a1a25; border: 1px solid rgba(139,92,246,0.3); border-radius: 10px; color: white; font-size: 14px; min-height: 80px;"></textarea>
                    <button onclick="submitRating()" style="margin-top: 14px; padding: 12px 24px; background: linear-gradient(135deg, #8b5cf6, #c084fc); border: none; border-radius: 10px; color: white; font-weight: 600; cursor: pointer;">Absenden</button>
                </div>
            </div>
        </main>
    </div>
    
    <script>
        let currentVideoId = null;
        let highlights = [];
        let highlightIndex = 0;
        
        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            document.getElementById('progress').classList.add('active');
            document.getElementById('progress-filename').textContent = file.name;
            
            const formData = new FormData();
            formData.append('file', file);
            
            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    document.getElementById('progress-percent').textContent = percent + '%';
                    document.getElementById('progress-fill').style.width = percent + '%';
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    const data = JSON.parse(xhr.responseText);
                    currentVideoId = data.video_id;
                    loadHighlights();
                }
            });
            
            xhr.open('POST', '/api/upload');
            xhr.send(formData);
        }
        
        async function loadHighlights() {
            const res = await fetch('/api/video/' + currentVideoId + '/highlights');
            highlights = await res.json();
            
            document.getElementById('progress').classList.remove('active');
            document.getElementById('dashboard').classList.add('active');
            
            // Animate metrics
            [85, 72, 60, 78, 65, 40].forEach((val, i) => {
                animateMetric('metric-' + ['pixel', 'motion', 'face', 'brightness', 'contrast', 'scene'][i], val);
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
                grid.innerHTML += `
                    <div class="highlight-card" onclick="showRating(${i})">
                        <div class="highlight-video" style="position:relative;">
                            <div class="highlight-play">▶</div>
                            <div class="highlight-duration">${Math.floor(dur / 60)}:${String(Math.floor(dur % 60)).padStart(2, '0')}</div>
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
            alert('Danke für Feedback!');
            document.getElementById('rating-section').classList.remove('active');
            if (highlightIndex < highlights.length - 1) {
                showRating(highlightIndex + 1);
            }
        }
        
        function showUrlInput() {
            const url = prompt('Video URL:');
            if (url) {
                // Handle URL upload
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
    from werkzeug.utils import secure_filename
    import uuid, os
    from datetime import datetime
    
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
    
    # Create demo highlights
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS videos (id, filename, upload_time, file_size, status)')
    c.execute('CREATE TABLE IF NOT EXISTS highlights (id, video_id, start_time, end_time, score, title, description, metrics)')
    c.execute('INSERT INTO videos VALUES (?, ?, ?, ?, ?)', (video_id, filename, datetime.now().isoformat(), os.path.getsize(path), 'uploaded'))
    
    types = [('Action-Höhepunkt', 'Spannende Action'), ('Emotionales Highlight', 'Starke Emotionen'), ('Szenenwechsel', 'Dynamischer Wechsel')]
    for i, (t, d) in enumerate(types):
        c.execute('INSERT INTO highlights VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                 (str(uuid.uuid4()), video_id, i*20, (i+1)*20, 95-i*10, t, d, '{"pixel":' + str(85-i*5) + ',"motion":' + str(90-i*5) + '}'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'video_id': video_id, 'status': 'uploaded'})

@app.route('/api/video/<vid>')
def get_video(vid):
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (vid,))
    v = c.fetchone()
    conn.close()
    if not v:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': v[0], 'filename': v[1], 'status': v[4]})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM highlights WHERE video_id = ?', (vid,))
    h = c.fetchall()
    conn.close()
    return jsonify([
        {'id': x[0], 'start_time': x[2], 'end_time': x[3], 'score': x[4], 'title': x[5], 'description': x[6], 'metrics': eval(x[7]) if len(x) > 7 else {}}
        for x in h
    ])

@app.route('/api/highlight/<hid>/rate', methods=['POST'])
def rate_highlight(hid):
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    data = request.get_json()
    c.execute('UPDATE highlights SET rating = ? WHERE id = ?', (data.get('rating'), hid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})