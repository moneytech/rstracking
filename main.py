import sqlite3
import os
import re
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

class TrackingRequestHandler(BaseHTTPRequestHandler):
  # GET
    def do_GET(self):
        # Send response status code
        split_path = self.path.split('/')
        if split_path[1] == 'api':
            if split_path[2] != secret_key:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(bytes("", "UTF8"))
                return
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            if self.path.endswith('history'):
                for row in c.execute(f'SELECT * FROM history ORDER BY access_time'):
                    self.wfile.write(bytes(str(row)[1:-1] + '\n', "UTF8"))
            elif self.path.endswith('trackers'):
                for row in c.execute(f'SELECT * FROM trackers ORDER BY hit_count'):
                    self.wfile.write(bytes(str(row)[1:-1] + '\n', "UTF8"))
            elif len(split_path) > 3:
                tracker_id = get_new_tracker(None, split_path[-1])
                self.wfile.write(bytes(tracker_id + '\n', "UTF8"))
            conn.commit()
            return
        try:
            uuid.UUID(split_path[-1])
            self.send_response(200)
            self.send_header('Content-type','image/gif')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            ip_address = self.address_string()
            user_agent = "NULL"
            accept_language = "NULL"
            if "User-Agent" in self.headers:
                user_agent = self.headers.get("User-Agent")
            if "Accept-Language" in self.headers:
                accept_language = self.headers.get("Accept-Language")            
            receive_request(split_path[-1].lower(), ip_address, user_agent, accept_language)
            self.wfile.write(ret_gif)
        except (ValueError):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(bytes("", "UTF8"))
        # Send headers
        return

def get_new_tracker(grouping, description):
    new_uuid = str(uuid.uuid4())
    try:
        c.execute(f"INSERT INTO trackers (uuid, grouping, description, hit_count) VALUES (?, ?, ?, 0)",
                                    (new_uuid, grouping, description))
        return new_uuid
    except sqlite3.IntegrityError:
        return "failure"

def receive_request(request_id, ip_address, user_agent, accept_language):
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

def start_server():
    print('starting server...') 
    # Server settings
    # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, TrackingRequestHandler)
    print('running server...')
    httpd.serve_forever()

gif_file = open("transparent.gif", "rb")
ret_gif = gif_file.read()
gif_file.close()
history_table = 'history'  # name of the history table
trackers_table = 'trackers'  # name of the trackers table
sqlite_file = 'tracking.db'    # name of the sqlite database file

try:
    if not os.path.isfile(sqlite_file):
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        initialize_database()
    else:
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
    secret_key = "70924a89154d5a7d8d60393a0880828e795bdb17b2cba43b"
    if secret_key == "":
        secret_key = os.urandom(24).hex()
    print(f"Your secret URL: /api/{secret_key}")
    start_server()
    conn.close()

except (KeyboardInterrupt, sqlite3.Error):
    conn.close()
