import json
import os
import re
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = Path(os.environ.get("APPOINTMENTS_DB", Path(__file__).with_name("appointments.sqlite3")))
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def connect():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("""CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        preferred_date TEXT NOT NULL,
        note TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    return connection


def validate(payload):
    if not isinstance(payload, dict):
        return "Enter a valid appointment request."
    name, email = payload.get("name"), payload.get("email")
    preferred_date, note = payload.get("preferredDate"), payload.get("note")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        return "Name is required and must be 100 characters or fewer."
    if not isinstance(email, str) or len(email) > 254 or not EMAIL_RE.fullmatch(email):
        return "Enter a valid email address."
    try:
        if not isinstance(preferred_date, str) or date.fromisoformat(preferred_date).isoformat() != preferred_date:
            raise ValueError
    except ValueError:
        return "Enter a valid preferred date."
    if not isinstance(note, str) or len(note) > 500:
        return "Note must be 500 characters or fewer."
    return None


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"))
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self.respond(204, {})

    def do_POST(self):
        if urlparse(self.path).path != "/api/appointments":
            return self.respond(404, {"error": "Not found."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16384:
                return self.respond(413, {"error": "Request is too large."})
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            return self.respond(400, {"error": "Send a valid JSON request."})
        error = validate(payload)
        if error:
            return self.respond(422, {"error": error})
        try:
            with connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO appointments (name, email, preferred_date, note) VALUES (?, ?, ?, ?)",
                    (payload["name"].strip(), payload["email"].strip(), payload["preferredDate"], payload["note"].strip()),
                )
                appointment_id = cursor.lastrowid
        except sqlite3.Error:
            return self.respond(500, {"error": "Your request could not be saved. Please try again."})
        self.respond(201, {"id": appointment_id, "status": "accepted", "message": "Your request was received."})

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    with ThreadingHTTPServer(("0.0.0.0", port), Handler) as server:
        print(f"Appointments API listening on port {port}")
        server.serve_forever()
