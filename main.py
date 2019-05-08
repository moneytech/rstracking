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
        print(split_path)
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
                for row in c.execute(f'SELECT * FROM {history_table} ORDER BY unix_time'):
                    print(row)
                    self.wfile.write(bytes(str(row)[1:-1] + '\n', "UTF8"))
            if self.path.endswith('trackers'):
                for row in c.execute(f'SELECT * FROM {trackers_table} ORDER BY hit_count'):
                    print(row)
                    self.wfile.write(bytes(str(row)[1:-1] + '\n', "UTF8"))
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
            receive_request(split_path[-1], ip_address, user_agent, accept_language)
            self.wfile.write(ret_gif)
        except (ValueError):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(bytes("", "UTF8"))
        # Send headers
        return

def receive_request(request_uuid, ip_address, user_agent, accept_language):
    c.execute(f"INSERT INTO {history_table} ({uuid_col}, ip_address, user_agent, accept_language, unix_time) VALUES (?, ?, ?, ?, ?)",
                                            (request_uuid, ip_address, user_agent, accept_language, int(time.time())))

    try:
        c.execute(f"INSERT INTO {trackers_table} ({uuid_col}, hit_count) VALUES (?, 1)",
                                    (request_uuid,))
    except sqlite3.IntegrityError:
        c.execute(f"UPDATE {trackers_table} SET hit_count = hit_count + 1 WHERE {uuid_col} = ?", (request_uuid,))
    conn.commit()
    print("received request")

def initialize_database():
    c.execute(f'CREATE TABLE IF NOT EXISTS {history_table} ({uuid_col} TEXT)')
    c.execute(f'CREATE TABLE IF NOT EXISTS {trackers_table} ({uuid_col} TEXT PRIMARY KEY)')

    add_history_cols = [("ip_address", "INTEGER"),
                        ("user_agent", "TEXT"),
                        ("accept_language", "TEXT"),
                        ("unix_time", "INTEGER"),
                        ("country", "TEXT")]

    add_trackers_cols = [("grouping", "TEXT"),
                         ("comment", "TEXT"),
                         ("hit_count", "INTEGER")]

    for col in add_history_cols:
        c.execute(f'ALTER TABLE {history_table} ADD COLUMN {col[0]} {col[1]}')

    for col in add_trackers_cols:
        c.execute(f'ALTER TABLE {trackers_table} ADD COLUMN {col[0]} {col[1]}')

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
history_table = 'history'  # name of the table to be created
trackers_table = 'trackers'  # name of the table to be created
sqlite_file = 'tracking.db'    # name of the sqlite database file
uuid_col = 'uuid' # name of the column

try:
    if not os.path.isfile(sqlite_file):
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
        initialize_database()
        conn.commit()
    else:
        conn = sqlite3.connect(sqlite_file)
        c = conn.cursor()
    secret_key = ""
    if secret_key == "":
        secret_key = os.urandom(24).hex()
    print(f"Your secret URL: /api/{secret_key}")
    start_server()
    conn.close()

except (KeyboardInterrupt, sqlite3.Error):
    conn.close()
