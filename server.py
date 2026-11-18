import json
import os
import re
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB_PATH = Path(os.environ.get("APPOINTMENTS_DB", Path(__file__).with_name("appointments.sqlite3")))
MAX_BODY = 16_384
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
FIELDS = {"name", "email", "preferredDate", "note"}


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, preferred_date TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    return connection


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        return "Provide name, email, preferredDate, and note."
    if any(not isinstance(payload[key], str) for key in FIELDS):
        return "All fields must be text."
    name, email, preferred, note = (payload[key].strip() for key in ("name", "email", "preferredDate", "note"))
    if not name or len(name) > 100:
        return "Name is required and must be 100 characters or fewer."
    if len(email) > 254 or not EMAIL.fullmatch(email):
        return "Enter a valid email address (254 characters or fewer)."
    try:
        if date.fromisoformat(preferred).isoformat() != preferred:
            raise ValueError
    except ValueError:
        return "Enter a valid preferred date in YYYY-MM-DD format."
    if len(note) > 500:
        return "Note must be 500 characters or fewer."
    return None


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_POST(self):
        if self.path != "/api/appointments":
            self.send_json(404, {"error": "Endpoint not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                self.send_json(400, {"error": "Request body is missing or too large."})
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_json(400, {"error": "Request body must be valid JSON."})
                return
            error = validate(payload)
            if error:
                self.send_json(422, {"error": error})
                return
            with connect() as db:
                db.execute("INSERT INTO appointments (name, email, preferred_date, note) VALUES (?, ?, ?, ?)", tuple(payload[key].strip() for key in ("name", "email", "preferredDate", "note")))
                request_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.send_json(201, {"id": request_id, "status": "accepted"})
        except sqlite3.Error:
            self.send_json(500, {"error": "The request could not be stored. Please try again."})

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    with connect():
        pass
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Appointments API listening on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
