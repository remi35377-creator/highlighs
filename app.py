from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Highlight AI</h1><p>Working!</p>'

@app.route('/api/upload', methods=['POST'])
def upload():
    return jsonify({'success': True, 'video_id': 'test123'})

@app.route('/api/video/<vid>')
def get_video(vid):
    return jsonify({'id': vid, 'status': 'completed'})

@app.route('/api/video/<vid>/highlights')
def highlights(vid):
    return jsonify([
        {'id': '1', 'start_time': 0, 'end_time': 30, 'score': 95, 'title': 'Action'},
        {'id': '2', 'start_time': 30, 'end_time': 60, 'score': 85, 'title': 'Highlight'}
    ])

# Required for Vercel
handler = app