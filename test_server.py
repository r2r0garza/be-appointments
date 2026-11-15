import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class AppointmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "test.sqlite3"
        self.patch = patch.object(server, "DB_PATH", self.db_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_valid_request_is_stored(self):
        payload = {"name": "A. Example", "email": "a@example.org", "preferredDate": "2030-04-12", "note": "Morning if possible"}
        self.assertIsNone(server.validate(payload))
        with server.connect() as db:
            db.execute("INSERT INTO appointments (name, email, preferred_date, note) VALUES (?, ?, ?, ?)", (payload["name"], payload["email"], payload["preferredDate"], payload["note"]))
            row = db.execute("SELECT name, email, preferred_date, note FROM appointments").fetchone()
        self.assertEqual(row, ("A. Example", "a@example.org", "2030-04-12", "Morning if possible"))

    def test_invalid_fields_rejected(self):
        payload = {"name": "", "email": "bad", "preferredDate": "2030-02-30", "note": "x" * 501}
        self.assertIsNotNone(server.validate(payload))
        with server.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0], 0)

    def test_malformed_payload_rejected(self):
        self.assertIsNotNone(server.validate(["not", "an", "object"]))

    def request(self, payload):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever)
        thread.start()
        try:
            connection = http.client.HTTPConnection(*httpd.server_address)
            body = payload if isinstance(payload, str) else json.dumps(payload)
            connection.request("POST", "/api/appointments", body=body, headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            result = json.loads(response.read())
            connection.close()
            return response.status, result
        finally:
            httpd.shutdown()
            thread.join()
            httpd.server_close()

    def test_http_valid_submission_persists_before_acceptance(self):
        status, result = self.request({"name": "A. Example", "email": "a@example.org", "preferredDate": "2030-04-12", "note": "Morning"})
        self.assertEqual(status, 201)
        self.assertEqual(result["status"], "accepted")
        with server.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0], 1)

    def test_http_invalid_request_is_not_stored(self):
        status, result = self.request({"name": "", "email": "bad", "preferredDate": "2030-04-12", "note": ""})
        self.assertEqual(status, 422)
        self.assertIn("error", result)
        with server.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0], 0)

    def test_http_storage_failure_returns_500(self):
        with patch.object(server, "connect", side_effect=server.sqlite3.OperationalError("unavailable")):
            status, result = self.request({"name": "A. Example", "email": "a@example.org", "preferredDate": "2030-04-12", "note": ""})
        self.assertEqual(status, 500)
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
