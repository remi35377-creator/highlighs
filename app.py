# Video-Verarbeitung für Vercel deaktiviert (zu groß)
# Nur Upload und API

import os
import json
import uuid
import sqlite3
import threading
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "database.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'webm'}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY, filename TEXT, original_path TEXT, upload_time TEXT,
        duration REAL, file_size INTEGER, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS highlights (
        id TEXT PRIMARY KEY, video_id TEXT, start_time REAL, end_time REAL, score REAL,
        title TEXT, description TEXT, rating TEXT, feedback TEXT)''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    video_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_{filename}")
    file.save(video_path)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO videos (id, filename, original_path, upload_time, file_size, status)
                  VALUES (?, ?, ?, ?, ?, ?)''',
              (video_id, filename, video_path, datetime.now().isoformat(), os.path.getsize(video_path), 'uploaded'))
    conn.commit()
    conn.close()
    
    # Simuliere Highlights (da keine OpenCV)
    create_demo_highlights(video_id)
    
    return jsonify({'video_id': video_id, 'filename': filename, 'status': 'uploaded'}), 200

def create_demo_highlights(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    types = [('Action-Moment', 'Spannende Action'), ('Highlight', 'Wichtiger Moment'), ('Ende', 'Abschluss')]
    for i, (title, desc) in enumerate(types):
        hid = str(uuid.uuid4())
        c.execute('INSERT INTO highlights (id, video_id, start_time, end_time, score, title, description) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (hid, video_id, i*10, (i+1)*10, 100-i*20, title, desc))
    conn.commit()
    conn.close()

@app.route('/api/upload/url', methods=['POST'])
def upload_url():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    import urllib.request
    video_id = str(uuid.uuid4())
    filename = secure_filename(url.split('/')[-1].split('?')[0]) or 'video.mp4'
    video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_{filename}")
    try:
        urllib.request.urlretrieve(url, video_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO videos (id, filename, original_path, upload_time, file_size, status)
                  VALUES (?, ?, ?, ?, ?, ?)''',
              (video_id, filename, video_path, datetime.now().isoformat(), os.path.getsize(video_path), 'uploaded'))
    conn.commit()
    conn.close()
    create_demo_highlights(video_id)
    return jsonify({'video_id': video_id, 'status': 'uploaded'}), 200

@app.route('/api/video/<video_id>', methods=['GET'])
def get_video(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    v = c.fetchone()
    conn.close()
    if not v:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': v[0], 'filename': v[1], 'status': v[5]})

@app.route('/api/video/<video_id>/highlights', methods=['GET'])
def get_highlights(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM highlights WHERE video_id = ?', (video_id,))
    highlights = c.fetchall()
    conn.close()
    return jsonify([{'id': h[0], 'start_time': h[2], 'end_time': h[3], 'score': h[4], 'title': h[5]} for h in highlights])

@app.route('/api/highlight/<highlight_id>/rate', methods=['POST'])
def rate_highlight(highlight_id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE highlights SET rating = ?, feedback = ? WHERE id = ?',
              (data.get('rating'), data.get('feedback', ''), highlight_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM videos ORDER BY upload_time DESC LIMIT 20')
    videos = c.fetchall()
    conn.close()
    return jsonify([{'id': v[0], 'filename': v[1], 'status': v[5]} for v in videos])

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.json
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token required'}), 400
    try:
        if GOOGLE_CLIENT_ID:
            from google.oauth2 import id_token
            from google.auth.transport import requests as gr
            id_info = id_token.verify_token(token, gr.Request(), GOOGLE_CLIENT_ID)
        else:
            id_info = {'sub': str(uuid.uuid4()), 'email': 'demo@example.com', 'name': 'Demo'}
        return jsonify({'success': True, 'user': id_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

handler = app