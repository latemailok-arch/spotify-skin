from flask import Flask, session, redirect, request, url_for, render_template, jsonify
import os, base64, hashlib, secrets, requests, time
from urllib.parse import urlencode

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me-please')

SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', 'YOUR_SPOTIFY_CLIENT_ID')
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/callback')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE = 'https://api.spotify.com/v1'

def generate_code_challenge(verifier: str) -> str:
    m = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(m).rstrip(b'=').decode('utf-8')

@app.route('/')
def index():
    logged_in = 'access_token' in session and session.get('access_token')
    return render_template('index.html', logged_in=logged_in)

@app.route('/login')
def login():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b'=').decode('utf-8')
    session['code_verifier'] = code_verifier
    code_challenge = generate_code_challenge(code_verifier)
    params = {
        'client_id': SPOTIFY_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'user-read-playback-state user-modify-playback-state user-read-private user-read-recently-played playlist-read-private',
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge,
        'show_dialog': 'true'
    }
    return redirect(AUTH_URL + '?' + urlencode(params))

@app.route('/callback')
def callback():
    error = request.args.get('error')
    if error:
        return f"Error from Spotify: {error}", 400
    code = request.args.get('code')
    code_verifier = session.get('code_verifier')
    if not code or not code_verifier:
        return "Missing code or verifier.", 400
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'code_verifier': code_verifier
    }
    resp = requests.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 400
    tok = resp.json()
    session['access_token'] = tok.get('access_token')
    session['refresh_token'] = tok.get('refresh_token')
    session['token_expires_at'] = int(time.time()) + tok.get('expires_in',3600)
    return redirect(url_for('index'))

def ensure_token():
    expires = session.get('token_expires_at', 0)
    if 'refresh_token' in session and time.time() > expires - 30:
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': SPOTIFY_CLIENT_ID
        }
        r = requests.post(TOKEN_URL, data=data)
        if r.status_code == 200:
            j = r.json()
            session['access_token'] = j.get('access_token')
            session['token_expires_at'] = int(time.time()) + j.get('expires_in',3600)

def proxy_get(path, params=None):
    ensure_token()
    token = session.get('access_token')
    if not token:
        return None, 401
    headers = {'Authorization': 'Bearer ' + token}
    resp = requests.get(API_BASE + path, headers=headers, params=params or {})
    return resp, resp.status_code if resp else (None, 401)

@app.route('/api/now_playing')
def now_playing():
    resp, status = proxy_get('/me/player/currently-playing')
    if resp is None:
        return jsonify({'error':'Not logged in'}), status
    if status != 200:
        if status == 204:
            return jsonify({'playing': False}), 200
        return resp.text, status
    return resp.text, 200, {'Content-Type':'application/json'}

@app.route('/api/recent')
def recent():
    resp, status = proxy_get('/me/player/recently-played', params={'limit':8})
    if resp is None:
        return jsonify({'error':'Not logged in'}), status
    if status != 200:
        return resp.text, status
    return resp.text, 200, {'Content-Type':'application/json'}

@app.route('/api/playlists')
def playlists():
    resp, status = proxy_get('/me/playlists', params={'limit':20})
    if resp is None:
        return jsonify({'error':'Not logged in'}), status
    if status != 200:
        return resp.text, status
    return resp.text, 200, {'Content-Type':'application/json'}

@app.route('/api/search')
def search():
    q = request.args.get('q') or ''
    if not q:
        return jsonify({'error':'q required'}), 400
    resp, status = proxy_get('/search', params={'q': q, 'type':'track,artist,album','limit':12})
    if resp is None:
        return jsonify({'error':'Not logged in'}), status
    if status != 200:
        return resp.text, status
    return resp.text, 200, {'Content-Type':'application/json'}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cert', help='Path to cert.pem for HTTPS', default=None)
    parser.add_argument('--key', help='Path to key.pem for HTTPS', default=None)
    args = parser.parse_args()
    port = int(os.environ.get('PORT', 5000))
    if args.cert and args.key:
        context = (args.cert, args.key)
        app.run(host='0.0.0.0', port=port, debug=True, ssl_context=context)
    else:
        app.run(host='0.0.0.0', port=port, debug=True)
