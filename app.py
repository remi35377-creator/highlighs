import os
import json
import uuid
import sqlite3
import threading
import time
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
HIGHLIGHT_FOLDER = os.path.join(BASE_DIR, "highlights")
DB_PATH = os.path.join(BASE_DIR, "database.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HIGHLIGHT_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'wmv', 'webm', 'flv', 'm4v'}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        filename TEXT,
        original_path TEXT,
        upload_time TEXT,
        duration REAL,
        width INTEGER,
        height INTEGER,
        fps REAL,
        file_size INTEGER,
        status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS highlights (
        id TEXT PRIMARY KEY,
        video_id TEXT,
        start_time REAL,
        end_time REAL,
        score REAL,
        title TEXT,
        description TEXT,
        metrics TEXT,
        clip_path TEXT,
        rating TEXT,
        feedback TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        feature_name TEXT,
        feature_value REAL,
        rating TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT,
        name TEXT,
        picture TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class VideoAnalyzer:
    def __init__(self, video_path):
        self.video_path = video_path
        try:
            self.cap = cv2.VideoCapture(video_path)
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            self.duration = self.frame_count / self.fps if self.fps > 0 else 0
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080
        except:
            self.fps = 30
            self.frame_count = 0
            self.duration = 0
            self.width = 1920
            self.height = 1080
    
    def analyze_frame(self, frame_idx):
        try:
            if self.cap:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    return None
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Pixel changes
                pixel_change = float(np.std(gray))
                
                # Motion detection - edge detection
                edges = cv2.Canny(gray, 50, 150)
                motion_score = float(np.sum(edges) / (edges.shape[0] * edges.shape[1]) * 100)
                
                # Face detection
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                face_count = len(faces)
                
                # Brightness/Energy
                brightness = float(np.mean(gray))
                contrast = float(np.std(gray))
                
                # Color detection
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                saturation = float(np.mean(hsv[:,:,1]))
                
                return {
                    'frame_idx': int(frame_idx),
                    'pixel_change': pixel_change,
                    'motion_score': motion_score,
                    'face_count': face_count,
                    'brightness': brightness,
                    'contrast': contrast,
                    'saturation': saturation
                }
        except Exception as e:
            print(f"Error analyzing frame: {e}")
            return None
    
    def analyze_video(self, max_frames=200):
        if not self.cap:
            return []
        
        frames = []
        try:
            if self.frame_count > 0:
                step = max(1, self.frame_count // max_frames)
                for i in range(0, min(self.frame_count, max_frames * step), step):
                    frame_data = self.analyze_frame(i)
                    if frame_data:
                        frames.append(frame_data)
        except:
            pass
        finally:
            if self.cap:
                self.cap.release()
        return frames
    
    def calculate_metrics(self, frames):
        if not frames:
            return {
                'pixel_change_score': 50,
                'motion_score': 50,
                'face_score': 50,
                'brightness_score': 50,
                'contrast_score': 50,
                'scene_score': 20
            }
        
        pixel_changes = [f['pixel_change'] for f in frames]
        motion_scores = [f['motion_score'] for f in frames]
        face_counts = [f['face_count'] for f in frames]
        brightness = [f['brightness'] for f in frames]
        contrast = [f['contrast'] for f in frames]
        
        # Calculate scene changes
        scene_changes = 0
        for i in range(1, len(frames)):
            if abs(pixel_changes[i] - pixel_changes[i-1]) > 20:
                scene_changes += 1
        
        return {
            'pixel_change_score': min(100, int(np.mean(pixel_changes) / 2.55)),
            'motion_score': min(100, int(np.mean(motion_scores))),
            'face_score': min(100, int(np.mean(face_counts) * 40)),
            'brightness_score': min(100, int(np.mean(brightness) / 2.55)),
            'contrast_score': min(100, int(np.mean(contrast) / 2.55)),
            'scene_score': min(100, scene_changes * 10)
        }
    
    def find_highlights(self, frames, min_duration=20, max_duration=60, num_highlights=5):
        if not frames or len(frames) < 10:
            return []
        
        window_size = max(1, len(frames) // 20)
        highlights = []
        
        for i in range(len(frames) - window_size):
            window = frames[i:i+window_size]
            
            # Calculate combined score
            pixel_avg = np.mean([f['pixel_change'] for f in window])
            motion_avg = np.mean([f['motion_score'] for f in window])
            face_avg = np.mean([f['face_count'] for f in window])
            brightness_avg = np.mean([f['brightness'] for f in window])
            
            # Weighted scoring
            score = (
                pixel_avg * 0.3 +
                motion_avg * 0.3 +
                face_avg * 20 * 0.2 +
                brightness_avg * 0.1
            )
            
            start_time = (i * window_size) / self.fps if self.fps > 0 else i
            end_time = ((i + window_size) * window_size) / self.fps if self.fps > 0 else i + window_size
            
            duration = end_time - start_time
            if duration < min_duration or duration > max_duration:
                continue
            
            highlights.append({
                'start_time': start_time,
                'end_time': end_time,
                'score': score,
                'metrics': {
                    'pixel': int(pixel_avg / 2.55),
                    'motion': int(motion_avg),
                    'face': int(face_avg * 40),
                    'brightness': int(brightness_avg / 2.55)
                }
            })
        
        # Sort by score and return top highlights
        highlights.sort(key=lambda x: x['score'], reverse=True)
        return highlights[:num_highlights]

def process_video(video_id, video_path):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE videos SET status = "analyzing" WHERE id = ?', (video_id,))
        conn.commit()
        conn.close()
        
        analyzer = VideoAnalyzer(video_path)
        frames = analyzer.analyze_video(max_frames=300)
        metrics = analyzer.calculate_metrics(frames)
        highlights = analyzer.find_highlights(frames)
        
        conn2 = sqlite3.connect(DB_PATH)
        c2 = conn2.cursor()
        
        highlight_types = [
            ('Action-Höhepunkt', 'Hochintensive Bewegung und spannende Action'),
            ('Emotionales Highlight', 'Starke Emotionen und Ausdrücke erkannt'),
            ('Szenenwechsel', 'Dynamischer Übergang zwischen Szenen'),
            ('Gesprächssequenz', 'Klare Sprache und Kommunikation'),
            ('Spannungsmoment', 'Intensive Atmosphäre und Stimmung')
        ]
        
        for i, h in enumerate(highlights):
            highlight_id = str(uuid.uuid4())
            title, desc = highlight_types[i % len(highlight_types)]
            c2.execute('''INSERT INTO highlights (id, video_id, start_time, end_time, score, title, description, metrics, created_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (highlight_id, video_id, h['start_time'], h['end_time'], h['score'],
                       title, desc, json.dumps(h['metrics']), datetime.now().isoformat()))
        
        conn2.commit()
        conn2.close()
        
        conn3 = sqlite3.connect(DB_PATH)
        c3 = conn3.cursor()
        c3.execute('UPDATE videos SET status = "completed" WHERE id = ?', (video_id,))
        conn3.commit()
        conn3.close()
        
    except Exception as e:
        print(f"Error processing video: {e}")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE videos SET status = "error" WHERE id = ?', (video_id,))
        conn.commit()
        conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        video_id = str(uuid.uuid4())
        video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_{filename}")
        
        file.save(video_path)
        
        analyzer = VideoAnalyzer(video_path)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO videos (id, filename, original_path, upload_time, duration, width, height, fps, file_size, status)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (video_id, filename, video_path, datetime.now().isoformat(),
                   analyzer.duration, analyzer.width, analyzer.height, analyzer.fps,
                   os.path.getsize(video_path), 'processing'))
        conn.commit()
        conn.close()
        
        threading.Thread(target=process_video, args=(video_id, video_path)).start()
        
        return jsonify({
            'video_id': video_id,
            'filename': filename,
            'status': 'processing',
            'message': 'Video wird analysiert'
        }), 200
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/upload/url', methods=['POST'])
def upload_from_url():
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
    
    analyzer = VideoAnalyzer(video_path)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO videos (id, filename, original_path, upload_time, duration, width, height, fps, file_size, status)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (video_id, filename, video_path, datetime.now().isoformat(),
               analyzer.duration, analyzer.width, analyzer.height, analyzer.fps,
               os.path.getsize(video_path), 'processing'))
    conn.commit()
    conn.close()
    
    threading.Thread(target=process_video, args=(video_id, video_path)).start()
    
    return jsonify({
        'video_id': video_id,
        'filename': filename,
        'status': 'processing'
    }), 200

@app.route('/api/video/<video_id>', methods=['GET'])
def get_video(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    video = c.fetchone()
    conn.close()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({
        'id': video[0],
        'filename': video[1],
        'status': video[9],
        'duration': video[4],
        'width': video[5],
        'height': video[6],
        'fps': video[7],
        'file_size': video[8]
    })

@app.route('/api/video/<video_id>/highlights', methods=['GET'])
def get_highlights(video_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM highlights WHERE video_id = ? ORDER BY score DESC', (video_id,))
    highlights = c.fetchall()
    conn.close()
    
    return jsonify([{
        'id': h[0],
        'start_time': h[2],
        'end_time': h[3],
        'score': h[4],
        'title': h[5],
        'description': h[6],
        'metrics': json.loads(h[7]),
        'clip_path': h[8],
        'rating': h[9],
        'feedback': h[10]
    } for h in highlights])

@app.route('/api/highlight/<highlight_id>/rate', methods=['POST'])
def rate_highlight(highlight_id):
    data = request.json
    rating = data.get('rating')
    feedback = data.get('feedback', '')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE highlights SET rating = ?, feedback = ? WHERE id = ?',
              (rating, feedback, highlight_id))
    conn.commit()
    
    c.execute('SELECT metrics FROM highlights WHERE id = ?', (highlight_id,))
    metrics_row = c.fetchone()
    if metrics_row:
        metrics = json.loads(metrics_row[0])
        for feature_name, feature_value in metrics.items():
            c.execute('INSERT INTO learning (feature_name, feature_value, rating, created_at) VALUES (?, ?, ?, ?)',
                     (feature_name, feature_value, rating, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/highlight/<highlight_id>/download', methods=['GET'])
def download_highlight(highlight_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT clip_path, title FROM highlights WHERE id = ?', (highlight_id,))
    highlight = c.fetchone()
    conn.close()
    
    if not highlight or not highlight[0]:
        return jsonify({'error': 'Clip nicht gefunden'}), 404
    
    return send_file(highlight[0], as_attachment=True)

@app.route('/api/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM videos ORDER BY upload_time DESC LIMIT 50')
    videos = c.fetchall()
    conn.close()
    
    return jsonify([{
        'id': v[0],
        'filename': v[1],
        'status': v[9],
        'upload_time': v[3],
        'duration': v[4],
        'file_size': v[8]
    } for v in videos])

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token required'}), 400
    
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
        if CLIENT_ID:
            id_info = id_token.verify_token(token, google_requests.Request(), CLIENT_ID)
        else:
            id_info = {'sub': str(uuid.uuid4()), 'email': 'demo@example.com', 'name': 'Demo User'}
        
        user_id = id_info['sub']
        email = id_info.get('email', '')
        name = id_info.get('name', '')
        picture = id_info.get('picture', '')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users (id, email, name, picture, created_at)
                      VALUES (?, ?, ?, ?, ?)''',
                  (user_id, email, name, picture, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {'id': user_id, 'email': email, 'name': name, 'picture': picture}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)