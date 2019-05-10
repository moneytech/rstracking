import sqlite3
import os
import io
from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)

gif_file = open("transparent.gif", "rb")
ret_gif = gif_file.read()
gif_file.close()

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

## GET route for tracking
@app.route('/trackers/<tracker_id>.gif')
def hit(tracker_id):
    try:
        uuid.UUID(tracker_id)
    except (ValueError):
        abort(404)
    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    accept_language = request.headers.get("Accept-Language")
    receive_request(tracker_id.lower(), ip_address, user_agent, accept_language)
    return send_file(io.BytesIO(ret_gif), mimetype='image/gif')

## GET route for history
@app.route('/api/<url_key>/history')
def get_history(url_key):
    if url_key != secret_key:
        abort(403)
    with sqlite3.connect(sqlite_file) as conn:
        c = conn.cursor()
        ret_list = []
        for row in c.execute(f'SELECT * FROM history ORDER BY access_time'):
            ret_list.append(row)
        return jsonify(ret_list)

## GET route for adding a tracker
@app.route('/api/<url_key>/add_tracker')
def add_tracker(url_key):
    if url_key != secret_key:
        abort(403)
    tracker_id = get_new_tracker(None, "random")
    return jsonify(tracker_id)

## GET route for list of trackers
@app.route('/api/<url_key>/trackers')
def get_trackers(url_key):
    if url_key != secret_key:
        abort(403)
    with sqlite3.connect(sqlite_file) as conn:
        c = conn.cursor()
        ret_list = []
        for row in c.execute(f'SELECT * FROM trackers ORDER BY hit_count'):
            ret_list.append(row)
        return jsonify(ret_list)

def get_new_tracker(grouping, description):
    with sqlite3.connect(sqlite_file) as conn:
        c = conn.cursor()
        new_uuid = str(uuid.uuid4())
        try:
            c.execute(f"INSERT INTO trackers (uuid, grouping, description, hit_count) VALUES (?, ?, ?, 0)",
                                        (new_uuid, grouping, description))
            conn.commit()
            return new_uuid
        except sqlite3.IntegrityError:
            return "failure"

def receive_request(request_id, ip_address, user_agent, accept_language):
    with sqlite3.connect(sqlite_file) as conn:
        c = conn.cursor()
        c.execute(f"INSERT INTO history"
                f"(tracker_id, ip_address, user_agent, accept_language, access_time)"
                f" VALUES (?, ?, ?, ?, ?)",
                    (request_id, ip_address, user_agent, accept_language, int(time.time())))
        try:
            c.execute(f"INSERT INTO trackers (uuid, hit_count) VALUES (?, 1)", (request_id,))
        except sqlite3.IntegrityError:
            c.execute(f"UPDATE trackers SET hit_count = hit_count + 1 WHERE uuid = ?", (request_id,))
        conn.commit()
        print("received request")

def initialize_database():
    c.execute(f'CREATE TABLE trackers ('
              f'uuid TEXT PRIMARY KEY NOT NULL,'
              f'grouping TEXT,'
              f'description TEXT,'
              f'hit_count INTEGER NOT NULL'
              f')')

    c.execute(f'CREATE TABLE history ('
              f'tracker_id TEXT NOT NULL,'
              f'ip_address INTEGER NOT NULL,'
              f'user_agent TEXT,'
              f'accept_language TEXT,'
              f'access_time INTEGER NOT NULL,'
              f'country TEXT,'
              f'FOREIGN KEY (tracker_id) REFERENCES trackers(uuid)'
              f')')
    conn.commit()

sqlite_file = 'tracking.db'    # name of the sqlite database file

if not os.path.isfile(sqlite_file):
    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()
    initialize_database()
    conn.close()
secret_key = "70924a89154d5a7d8d60393a0880828e795bdb17b2cba43b"
if secret_key == "":
    secret_key = os.urandom(24).hex()
print(f"Your secret URL: /api/{secret_key}")

if __name__ == "__main__":
    # Only for debugging while developing
    app.run(host='0.0.0.0', debug=True, port=os.environ.get('PORT', 8080))
    