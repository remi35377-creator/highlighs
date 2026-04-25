from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Highlight AI</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #fff; min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { font-size: 40px; background: linear-gradient(135deg, #8b5cf6, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 40px 0; }
        .upload-zone { border: 2px dashed #8b5cf6; border-radius: 16px; padding: 60px; text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-zone:hover { background: rgba(139,92,246,0.1); }
        .btn { background: linear-gradient(135deg, #8b5cf6, #c084fc); border: none; padding: 16px 32px; border-radius: 12px; color: white; font-size: 18px; font-weight: 600; cursor: pointer; margin: 10px; }
        input { display: none; }
        .result { margin-top: 30px; padding: 20px; background: #15151f; border-radius: 12px; }
        .highlight { padding: 16px; margin: 10px 0; background: #1a1a25; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Highlight AI</h1>
        <p style="color: #888; margin-bottom: 30px;">Video Highlights Extractor</p>
        
        <div class="upload-zone" onclick="document.getElementById('file').click()">
            <p style="font-size: 48px;">📁</p>
            <p>Click to upload video</p>
        </div>
        
        <input type="file" id="file" accept="video/*" onchange="upload()">
        
        <div id="result"></div>
    </div>
    
    <script>
    const API = '';
    async function upload() {
        const file = document.getElementById('file').files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        document.getElementById('result').innerHTML = '<p>Uploading...</p>';
        
        try {
            const res = await fetch(API + '/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            
            if (data.video_id) {
                poll(data.video_id);
            } else {
                document.getElementById('result').innerHTML = '<p>Error: ' + (data.error || 'Unknown') + '</p>';
            }
        } catch(e) {
            document.getElementById('result').innerHTML = '<p>Error: ' + e.message + '</p>';
        }
    }
    
    async function poll(vid) {
        document.getElementById('result').innerHTML = '<p>Processing...</p>';
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 2000));
            const res = await fetch(API + '/api/video/' + vid);
            const data = await res.json();
            if (data.status === 'uploaded' || data.status === 'completed') {
                showHighlights(vid);
                return;
            }
        }
    }
    
    async function showHighlights(vid) {
        const res = await fetch(API + '/api/video/' + vid + '/highlights');
        const data = await res.json();
        
        let html = '<h2>Highlights</h2>';
        data.forEach(h => {
            html += '<div class="highlight"><b>' + h.title + '</b><br>Time: ' + h.start_time + 's - ' + h.end_time + 's<br>Score: ' + h.score + '</div>';
        });
        document.getElementById('result').innerHTML = html;
    }
    <\/script>
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
        return jsonify({'error': 'No file'})
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'})
    
    video_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    os.makedirs('uploads', exist_ok=True)
    path = f'uploads/{video_id}_{filename}'
    file.save(path)
    
    # Create demo highlights
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS videos (id, filename, original_path, upload_time, file_size, status)')
    c.execute('CREATE TABLE IF NOT EXISTS highlights (id, video_id, start_time, end_time, score, title, description)')
    c.execute('INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?)', (video_id, filename, path, datetime.now().isoformat(), os.path.getsize(path), 'uploaded'))
    
    types = [('Action', 'Action scene'), ('Highlight', 'Important moment'), ('Ending', 'Conclusion')]
    for i, (t, d) in enumerate(types):
        from datetime import datetime
        c.execute('INSERT INTO highlights VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                 (str(uuid.uuid4()), video_id, i*10, (i+1)*10, 100-i*20, t, d))
    
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
def get_highlights(vid):
    import sqlite3
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM highlights WHERE video_id = ?', (vid,))
    h = c.fetchall()
    conn.close()
    return jsonify([{'id': x[0], 'start_time': x[2], 'end_time': x[3], 'score': x[4], 'title': x[5]} for x in h])

handler = app