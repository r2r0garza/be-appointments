import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class AppointmentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "appointments.sqlite3"
        self.path_patch = patch.object(app, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/appointments"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def post(self, payload):
        request = Request(self.url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        return response.status, json.loads(response.read())

    def test_valid_request_is_persisted_before_accepted_response(self):
        payload = {"name": "Avery Lane", "email": "avery@example.com", "preferredDate": "2030-04-12", "note": "Morning, if available."}
        status, body = self.post(payload)
        self.assertEqual(status, 201)
        self.assertEqual(body["status"], "accepted")
        with app.connect() as connection:
            row = connection.execute("SELECT name, email, preferred_date, note FROM appointments").fetchone()
        self.assertEqual(row, ("Avery Lane", "avery@example.com", "2030-04-12", "Morning, if available."))

    def test_invalid_request_is_not_stored(self):
        payload = {"name": "Avery", "email": "invalid", "preferredDate": "2030-04-12", "note": ""}
        status, _ = self.post(payload)
        self.assertEqual(status, 422)
        self.assertFalse(self.db_path.exists())

    def test_storage_error_does_not_return_accepted(self):
        payload = {"name": "Avery", "email": "avery@example.com", "preferredDate": "2030-04-12", "note": ""}
        with patch.object(app, "connect", side_effect=app.sqlite3.Error("disk unavailable")):
            status, body = self.post(payload)
        self.assertEqual(status, 500)
        self.assertNotEqual(body.get("status"), "accepted")


if __name__ == "__main__":
    unittest.main()
