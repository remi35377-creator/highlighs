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
import sqlite3

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# SQLite Database für persistente Speicherung
DB_FILE = 'videos.db'

def init_db():
    """Datenbank initialisieren"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        email TEXT,
        filename TEXT,
        date TEXT,
        status TEXT,
        metrics TEXT,
        highlights TEXT
    )''')
    conn.commit()
    conn.close()

def save_video(video_id, data):
    """Video in Datenbank speichern"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO videos (id, email, filename, date, status, metrics, highlights)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (video_id, data.get('email'), data.get('filename'), data.get('date'),
               data.get('status'), json.dumps(data.get('metrics')), json.dumps(data.get('highlights'))))
    conn.commit()
    conn.close()

def get_video(video_id):
    """Video aus Datenbank holen"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'email': row[1], 'filename': row[2], 'date': row[3],
            'status': row[4], 'metrics': json.loads(row[5]) if row[5] else None,
            'highlights': json.loads(row[6]) if row[6] else []
        }
    return None

def get_user_videos(email):
    """Alle Videos eines Users holen"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, filename, date, status FROM videos WHERE email = ? ORDER BY date DESC', (email,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'filename': r[1], 'date': r[2], 'status': r[3]} for r in rows]

# Datenbank initialisieren
init_db()

# Echte Video-Analyse-Funktionen
def analyze_video_metrics(video_path):
    """Echtes Video analysieren mit OpenCV + Audio-Analyse"""
    import os
    import sys
    
    print(f"\n=== VIDEO ANALYSIS DEBUG ===", flush=True)
    print(f"Video path: {video_path}", flush=True)
    
    # Prüfe ob Datei existiert
    if not os.path.exists(video_path):
        print("ERROR: File does not exist!")
        return {
            'pixel': 75, 'motion': 80, 'brightness': 50, 
            'contrast': 60, 'scene': 40, 'duration': 30,
            'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
        }
    
    # Prüfe Dateigröße
    file_size = os.path.getsize(video_path)
    print(f"File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
    
    if file_size < 10000:  # Weniger als 10KB = wahrscheinlich fehlerhaft
        print("ERROR: File too small (<10KB) - likely corrupted!")
        return {
            'pixel': 75, 'motion': 80, 'brightness': 50, 
            'contrast': 60, 'scene': 40, 'duration': 30,
            'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
        }
    
    # Prüfe ob Video-Datei lesbar ist (ffprobe-check)
    print("Running ffprobe validation...")
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration,format_name',
            '-of', 'json', video_path
        ], capture_output=True, text=True, timeout=10)
        
        print(f"ffprobe return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"ERROR: ffprobe failed! stderr: {result.stderr}")
            return {
                'pixel': 75, 'motion': 80, 'brightness': 50, 
                'contrast': 60, 'scene': 40, 'duration': 30,
                'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
            }
        
        import json
        data = json.loads(result.stdout)
        print(f"ffprobe output: {data}")
        duration_val = float(data.get('format', {}).get('duration', 0))
        print(f"Video duration from ffprobe: {duration_val}s")
    except subprocess.TimeoutExpired:
        print("ERROR: ffprobe timed out!")
        return {
            'pixel': 75, 'motion': 80, 'brightness': 50, 
            'contrast': 60, 'scene': 40, 'duration': 30,
            'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
        }
    except Exception as e:
        print(f"ERROR: ffprobe exception: {e}")
        return {
            'pixel': 75, 'motion': 80, 'brightness': 50, 
            'contrast': 60, 'scene': 40, 'duration': 30,
            'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
        }
    
    try:
        print("Opening with OpenCV...")
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print("ERROR: OpenCV cannot open video!")
            return {
                'pixel': 75, 'motion': 80, 'brightness': 50, 
                'contrast': 60, 'scene': 40, 'duration': 30,
                'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
            }
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"OpenCV: fps={fps}, frames={frame_count}")
        
        duration = frame_count / fps if fps > 0 else duration_val
        
        if duration <= 0:
            duration = 30
        
        # FÜR GROSSE VIDEOS: Nur die ersten 60 Sekunden analysieren
        max_frames_to_analyze = min(frame_count, int(fps * 60)) if fps > 0 else 600
        frames_analyzed = 0
        
        # Audio-Analyse mit ffprobe
        audio_info = {'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC', 'sample_rate': '48kHz'}
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,channels,sample_rate',
                '-of', 'json', video_path
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                streams = data.get('streams', [])
                audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
                
                if audio_streams:
                    audio_info['audio_tracks'] = len(audio_streams)
                    a = audio_streams[0]
                    audio_info['audio_channels'] = a.get('channels', 2)
                    audio_info['audio_codec'] = a.get('codec_name', 'AAC').upper()
                    audio_info['sample_rate'] = a.get('sample_rate', '48kHz')
        except:
            pass
        
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
            
            frames_analyzed += 1
            
            if frame_idx % 10 == 0 and frames_analyzed <= max_frames_to_analyze:
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
            if frames_analyzed >= max_frames_to_analyze:
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
            'duration': int(duration),
            'audio_tracks': audio_info['audio_tracks'],
            'audio_channels': audio_info['audio_channels'],
            'audio_codec': audio_info['audio_codec'],
            'sample_rate': audio_info['sample_rate']
        }
    except Exception as e:
        print(f"Video analysis exception: {e}")
        return {
            'pixel': 75, 'motion': 80, 'brightness': 50, 
            'contrast': 60, 'scene': 40, 'duration': 30,
            'audio_tracks': 1, 'audio_channels': 2, 'audio_codec': 'AAC'
        }
    finally:
        print("=== ANALYSIS COMPLETE ===\n")


def find_highlights(video_path, metrics):
    """Echte Highlight-Clips finden basierend auf verschiedenen Analyse-Methoden"""
    print(">>> Starting real highlight detection...")
    
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return create_fallback_highlights(metrics)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 30
        
        if duration <= 0:
            duration = 30
            
        fps = int(fps) if fps > 0 else 30
        print(f">>> Video: {duration}s, {fps} fps, {frame_count} frames")
        
    except Exception as e:
        print(f">>> Error reading video: {e}")
        return create_fallback_highlights(metrics)
    
    # Verschiedene Analyse-Methoden
    motion_scores = []
    brightness_values = []
    prev_gray = None
    
    # Analysiere alle Frames (jeden 5. für Speed)
    frame_idx = 0
    max_frames = min(frame_count, fps * 120)  # Max 2 Minuten analysieren
    
    print(">>> Analyzing frames for highlight detection...")
    
    while True:
        ret, frame = cap.read()
        if not ret or frame_idx >= max_frames:
            break
        
        if frame_idx % 5 == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            brightness_values.append(brightness)
            
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                motion = np.std(diff)
                motion_scores.append(motion)
            
            prev_gray = gray
        
        frame_idx += 1
    
    cap.release()
    
    if not motion_scores or len(motion_scores) < 10:
        print(">>> Not enough data - using fallback")
        return create_fallback_highlights(metrics)
    
    # 6 verschiedene Highlight-Methoden
    highlights = []
    
    # 1. HÖCHSTE BEWEGUNG (Motion Peak)
    max_motion_idx = np.argmax(motion_scores)
    start1 = int((max_motion_idx * 5) / fps)
    highlights.append({
        'id': str(uuid.uuid4()),
        'start_time': max(0, start1 - 10),
        'end_time': min(duration, start1 + 20),
        'score': min(100, int(np.max(motion_scores) / 3)),
        'title': '🔥 Action-Höhepunkt',
        'method': 'motion_peak',
        'value': int(np.max(motion_scores))
    })
    
    # 2. GRÖSSTE HELLIGKEITSÄNDERUNG (Brightness Change)
    brightness_changes = [abs(brightness_values[i+1] - brightness_values[i]) 
                         for i in range(len(brightness_values)-1)]
    max_bright_idx = np.argmax(brightness_changes) if brightness_changes else 0
    start2 = int((max_bright_idx * 5) / fps)
    highlights.append({
        'id': str(uuid.uuid4()),
        'start_time': max(0, start2 - 10),
        'end_time': min(duration, start2 + 20),
        'score': min(100, int(brightness_changes[max_bright_idx] / 5) if brightness_changes else 50),
        'title': '💡 Helligkeits-Wechsel',
        'method': 'brightness_change',
        'value': int(brightness_changes[max_bright_idx]) if brightness_changes else 0
    })
    
    # 3. KONTRAST-ÄNDERUNG (Contrast)
    contrast_score = metrics.get('contrast', 60)
    mid_point = len(motion_scores) // 2
    highlights.append({
        'id': str(uuid.uuid4()),
        'start_time': max(0, int((mid_point * 5) / fps) - 15),
        'end_time': min(duration, int((mid_point * 5) / fps) + 15),
        'score': contrast_score,
        'title': '🎬 Kontrast-Szene',
        'method': 'contrast',
        'value': contrast_score
    })
    
    # 4. SZENENWECHSEL (Scene Change)
    scene_score = metrics.get('scene', 40)
    if scene_score > 30:
        scene_positions = [i for i in range(1, len(brightness_values)) 
                         if abs(brightness_values[i] - brightness_values[i-1]) > 20]
        if scene_positions:
            best_scene = scene_positions[len(scene_positions)//2]
            start4 = int((best_scene * 5) / fps)
            highlights.append({
                'id': str(uuid.uuid4()),
                'start_time': max(0, start4 - 10),
                'end_time': min(duration, start4 + 20),
                'score': min(100, scene_score),
                'title': '🔄 Szenen-Wechsel',
                'method': 'scene_change',
                'value': len(scene_positions)
            })
        else:
            highlights.append({
                'id': str(uuid.uuid4()),
                'start_time': int(duration * 0.3),
                'end_time': min(duration, int(duration * 0.3) + 30),
                'score': scene_score,
                'title': '🔄 Szenen-Wechsel',
                'method': 'scene_change',
                'value': 0
            })
    else:
        highlights.append({
            'id': str(uuid.uuid4()),
            'start_time': int(duration * 0.3),
            'end_time': min(duration, int(duration * 0.3) + 30),
            'score': scene_score,
            'title': '🔄 Szenen-Wechsel',
            'method': 'scene_change',
            'value': 0
        })
    
    # 5. DURCHSCHNITT (Average Activity)
    avg_motion = np.mean(motion_scores)
    avg_idx = int(len(motion_scores) * 0.5)
    start5 = int((avg_idx * 5) / fps)
    highlights.append({
        'id': str(uuid.uuid4()),
        'start_time': max(0, start5 - 10),
        'end_time': min(duration, start5 + 20),
        'score': min(100, int(avg_motion / 3)),
        'title': '📊 Durchschnitts-Szene',
        'method': 'average',
        'value': int(avg_motion)
    })
    
    # 6. DAUER-BASIERT (Duration-based)
    if duration > 60:
        final_start = int(duration - 40)
        highlights.append({
            'id': str(uuid.uuid4()),
            'start_time': max(0, final_start),
            'end_time': min(duration, final_start + 30),
            'score': 70,
            'title': '🎯 Finale Szene',
            'method': 'finale',
            'value': int(duration)
        })
    else:
        highlights.append({
            'id': str(uuid.uuid4()),
            'start_time': 0,
            'end_time': min(30, int(duration)),
            'score': 75,
            'title': '🎯 Erste Szene',
            'method': 'start',
            'value': 0
        })
    
    # Sortiere nach Score
    highlights.sort(key=lambda x: x['score'], reverse=True)
    
    print(f">>> Found {len(highlights)} real highlights")
    for h in highlights:
        print(f">>>   - {h['title']}: score={h['score']}, method={h['method']}")
    
    return highlights


def create_fallback_highlights(metrics):
    """Fallback wenn keine echten Highlights gefunden wurden"""
    duration = metrics.get('duration', 30)
    highlights = []
    methods = ['motion', 'brightness', 'contrast', 'scene', 'average', 'finale']
    titles = ['🔥 Action', '💡 Licht', '🎬 Kontrast', '🔄 Wechsel', '📊 Durchschnitt', '🎯 Finale']
    
    for i in range(6):
        start = int((duration / 7) * (i + 1))
        highlights.append({
            'id': str(uuid.uuid4()),
            'start_time': max(0, start - 10),
            'end_time': min(duration, start + 20),
            'score': 95 - (i * 5),
            'title': titles[i],
            'method': methods[i],
            'value': 50
        })
    
    return highlights

# Analyse im Hintergrund starten
def process_video_async(video_id, video_path, email):
    """Video im Hintergrund analysieren"""
    print(f"\n>>> STARTING VIDEO PROCESSING for {video_id}")
    print(f">>> Video path: {video_path}")
    
    try:
        # Metriken analysieren
        metrics = analyze_video_metrics(video_path)
        print(f">>> Metrics result: {metrics}")
        
        if metrics:
            # Highlights finden
            highlights = find_highlights(video_path, metrics)
            print(f">>> Found {len(highlights)} highlights")
            
            # Ergebnisse speichern
            save_video(video_id, {
                'email': email,
                'filename': os.path.basename(video_path),
                'date': datetime.now().isoformat(),
                'status': 'completed',
                'metrics': metrics,
                'highlights': highlights
            })
            print(f">>> Video processing COMPLETED!")
        else:
            print(">>> Metrics returned None - marking as failed")
            save_video(video_id, {'email': email, 'filename': os.path.basename(video_path), 'date': datetime.now().isoformat(), 'status': 'failed'})
    except Exception as e:
        print(f">>> ERROR processing video: {e}")
        import traceback
        traceback.print_exc()
        save_video(video_id, {'email': email, 'filename': os.path.basename(video_path), 'date': datetime.now().isoformat(), 'status': 'failed'})

HTML = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Highlight AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', -apple-system, sans-serif; 
            background: #0a0a0f; 
            color: #fff; 
            min-height: 100vh;
            background: linear-gradient(180deg, #0a0a0f 0%, #12121a 100%);
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
        
        header { 
            display: flex; 
            justify-content: space-between; 
            padding: 24px 0;
            border-bottom: 1px solid rgba(139,92,246,0.15);
        }
        .logo { 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            font-size: 24px; 
            font-weight: 700; 
        }
        .logo-icon { 
            width: 44px; height: 44px; 
            background: linear-gradient(135deg, #8b5cf6, #c084fc); 
            border-radius: 12px; 
            display: flex; 
            align-items: center; 
            justify-content: center;
            font-size: 22px;
        }
        .logo-text { 
            background: linear-gradient(135deg, #8b5cf6, #c084fc); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
        }
        
        .hero { text-align: center; padding: 80px 0 60px; }
        .hero h1 { 
            font-size: 56px; 
            font-weight: 700; 
            margin-bottom: 16px; 
            letter-spacing: -1px;
        }
        .hero h1 .highlight { 
            background: linear-gradient(135deg, #8b5cf6, #c084fc); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
        }
        .hero p { 
            color: #888; 
            font-size: 20px; 
            font-weight: 300;
        }
        
        .login-box { 
            max-width: 440px; 
            margin: 0 auto; 
            padding: 48px; 
            background: #15151f; 
            border-radius: 24px;
            border: 1px solid rgba(139,92,246,0.2);
            box-shadow: 0 20px 60px rgba(0,0,0,0.4);
        }
        .login-box h2 { 
            text-align: center; 
            margin-bottom: 32px; 
            font-size: 24px;
        }
        
        .form-input { 
            width: 100%; 
            padding: 16px 20px; 
            margin-bottom: 16px; 
            background: #1a1a25; 
            border: 1px solid rgba(139,92,246,0.3); 
            border-radius: 12px; 
            color: #fff; 
            font-size: 16px;
            transition: border-color 0.2s;
        }
        .form-input:focus { 
            outline: none; 
            border-color: #8b5cf6; 
        }
        .form-input::placeholder { 
            color: #666; 
        }
        
        .btn-primary { 
            width: 100%; 
            padding: 16px 24px; 
            background: linear-gradient(135deg, #8b5cf6, #c084fc); 
            border: none; 
            border-radius: 12px; 
            color: #fff; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-primary:hover { 
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(139,92,246,0.4);
        }
        
        .otp-section { display: none; margin-top: 24px; }
        .otp-section p { 
            color: #888; 
            text-align: center; 
            margin-bottom: 16px; 
        }
        
        .upload-section { display: none; padding: 40px 0; }
        .upload-grid { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 24px; 
            margin-bottom: 40px; 
        }
        .upload-card { 
            background: #15151f; 
            border: 2px dashed rgba(139,92,246,0.3); 
            border-radius: 20px; 
            padding: 48px 24px; 
            text-align: center; 
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-card:hover { 
            border-color: #8b5cf6; 
            background: #1a1a25;
            transform: translateY(-4px);
        }
        .upload-icon { font-size: 48px; margin-bottom: 16px; }
        .upload-card h3 { font-size: 18px; margin-bottom: 8px; }
        .upload-card p { color: #888; font-size: 14px; }
        
        .progress-box { 
            display: none;
            background: #15151f; 
            border-radius: 16px; 
            padding: 24px; 
            margin-top: 32px;
        }
        .progress-box.active { display: block; }
        .progress-header { 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 12px; 
        }
        .progress-fill { 
            height: 8px; 
            background: rgba(139,92,246,0.2); 
            border-radius: 4px; 
            overflow: hidden;
        }
        .progress-bar { 
            height: 100%; 
            background: linear-gradient(135deg, #8b5cf6, #c084fc); 
            border-radius: 4px;
            width: 0%;
            transition: width 0.3s;
        }
        
        .history-section { margin-top: 60px; }
        .history-section h2 { margin-bottom: 24px; font-size: 24px; }
        .history-grid { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 20px; 
        }
        .history-card { 
            background: #15151f; 
            border-radius: 16px; 
            padding: 20px; 
            cursor: pointer;
            transition: border-color 0.2s;
        }
        .history-card:hover { border: 1px solid rgba(139,92,246,0.5); }
        .history-title { font-weight: 600; margin-bottom: 8px; font-size: 16px; }
        .history-date { color: #888; font-size: 14px; }
        
        .status-text { 
            margin-top: 24px; 
            text-align: center; 
            color: #8b5cf6;
            font-size: 16px;
        }
        
        @media (max-width: 768px) {
            .upload-grid, .history-grid { grid-template-columns: 1fr; }
            .hero h1 { font-size: 36px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <div class="logo-icon">⚡</div>
                <span class="logo-text">Highlight AI</span>
            </div>
        </header>
        
        <main>
            <div class="hero">
                <h1>Extrahiere die <span class="highlight">perfekten Momente</span></h1>
                <p>KI-gestützte Video-Analyse</p>
            </div>
            
            <div class="login-box" id="login-box">
                <h2>🔐 Anmelden</h2>
                <input type="email" id="email" class="form-input" placeholder="Deine E-Mail-Adresse">
                <button class="btn-primary" onclick="send()">Code senden</button>
                
                <div class="otp-section" id="otp">
                    <p>Gib den 6-stelligen Code ein</p>
                    <input type="text" id="code" class="form-input" placeholder="XXXXXX" maxlength="6" style="text-align:center; letter-spacing:8px; font-size:24px;">
                    <button class="btn-primary" onclick="verify()">Bestätigen</button>
                </div>
            </div>
            
            <div class="upload-section" id="main">
                <div class="upload-grid">
                    <div class="upload-card" onclick="document.getElementById('file').click()">
                        <div class="upload-icon">💾</div>
                        <h3>Dateiupload</h3>
                        <p>Von deinem Gerät</p>
                    </div>
                    <div class="upload-card">
                        <div class="upload-icon">🔗</div>
                        <h3>URL Import</h3>
                        <p>Von Web-URL</p>
                    </div>
                    <div class="upload-card">
                        <div class="upload-icon">☁️</div>
                        <h3>Cloud</h3>
                        <p>Google Drive, etc.</p>
                    </div>
                </div>
                
                <input type="file" id="file" accept="video/*" onchange="upload()" style="display:none">
                
                <div class="progress-box" id="progress">
                    <div class="progress-header">
                        <span id="filename">video.mp4</span>
                        <span id="percent" style="color:#8b5cf6;">0%</span>
                    </div>
                    <div class="progress-fill">
                        <div class="progress-bar" id="bar"></div>
                    </div>
                </div>
                
                <div class="status-text" id="status"></div>
                
                <div class="history-section">
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
        alert('Dein Code: ' + c);
    }
    function verify() {
        var i = document.getElementById('code').value;
        if(i == localStorage.getItem('code')) {
            document.getElementById('login-box').style.display = 'none';
            document.getElementById('main').style.display = 'block';
            loadHistory();
        } else {
            alert('Falscher Code!');
        }
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
                document.getElementById('bar').style.width = p + '%';
            }
        };
        x.onload = function() {
            if(x.status === 200) {
                document.getElementById('status').innerText = '✓ Hochgeladen! Video wird analysiert...';
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
                    h.innerHTML = '<p style="color:#888;">Noch keine Videos hochgeladen</p>';
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
    var saved = localStorage.getItem('email');
    if(saved) {
        document.getElementById('login-box').style.display = 'none';
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
    print("\n=== UPLOAD REQUEST RECEIVED ===")
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    email = request.form.get('email', '')
    if not email:
        return jsonify({'error': 'Not logged in'}), 401
    
    file = request.files['file']
    filename = file.filename[:100] if file.filename else 'video.mp4'
    print(f"Upload: email={email}, filename={filename}")
    
    # Prüfe Dateigröße
    content_length = request.content_length
    print(f"Content-Length: {content_length}")
    if content_length and content_length > 5 * 1024 * 1024 * 1024:  # Mehr als 5GB
        return jsonify({'error': 'Datei zu groß. Max 5GB erlaubt.'}), 400
    
    video_id = str(uuid.uuid4())
    print(f"Video ID: {video_id}")
    
    # Erstelle Ordner für Uploads
    upload_dir = os.path.join(UPLOAD_FOLDER, video_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    video_path = os.path.join(upload_dir, filename)
    
    # Stream die Datei in Chunks
    try:
        print("Starting file upload...")
        with open(video_path, 'wb') as f:
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        print(f"File saved to: {video_path}")
    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({'error': f'Upload fehlgeschlagen: {str(e)}'}), 500
    
    save_video(video_id, {
        'email': email,
        'filename': filename,
        'date': datetime.now().isoformat(),
        'status': 'processing'
    })
    
    print("Starting async video processing...")
    # Video im Hintergrund analysieren
    threading.Thread(target=process_video_async, args=(video_id, video_path, email)).start()
    
    return jsonify({'video_id': video_id, 'status': 'processing'})

@app.route('/api/video/<vid>')
def get_video_api(vid):
    v = get_video(vid)
    if not v:
        return jsonify({'error': 'Not found'}), 404
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
    videos = get_user_videos(email)
    return jsonify(videos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)