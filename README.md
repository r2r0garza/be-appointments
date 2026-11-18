# Appointments API

A small Python standard-library HTTP API with SQLite persistence for appointment requests. Successful submission means received and stored; it does not mean an appointment is booked or confirmed.

## Run

Requires Python 3.10+; there are no third-party dependencies.

```sh
python3 app.py
```

The server listens on port `8000` by default. Set `PORT` to change it, `APPOINTMENTS_DB` to choose the SQLite file (defaults to `appointments.sqlite3` beside `app.py`), and `FRONTEND_ORIGIN` to configure the allowed frontend origin (defaults to `http://localhost:5173`).

## API

`POST /api/appointments` accepts JSON with `name` (required, 1–100 characters after trimming), `email` (required, valid email syntax, at most 254 characters), `preferredDate` (required ISO `YYYY-MM-DD`), and `note` (required string, at most 500 characters; may be empty). The API independently validates all fields. Invalid JSON returns `400`, invalid data returns `422` with an `error` message, and storage failures return `500`. A successful durable insert returns `201` with `{ "id": 1, "status": "accepted", "message": "Your request was received." }`.

The frontend uses `/api/appointments` through the Vite proxy. Set `VITE_API_PROXY_TARGET` for a non-default backend host, or `VITE_API_BASE_URL` to have the browser call an absolute API base URL directly.

## Test

```sh
python3 -m unittest -v
```
