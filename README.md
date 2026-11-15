# Appointments Backend

Backend for a small appointment-request app. A user submits their name, email, preferred date, and a short note; the backend validates the request and stores it, then reports whether it was accepted.

## Responsibilities

- Accept appointment requests from the frontend.
- Validate required fields and reject invalid requests with useful, consistent feedback.
- Store valid requests so accepted submissions are retained.
- Return a clear success or failure response that the frontend can display.

## Request data

Each request contains a name, email address, preferred date, and short note. Validation rules should be explicit and shared with the frontend/API contract as the implementation takes shape. The app confirms that a request was accepted; that does not imply the appointment is booked or confirmed unless scheduling behavior is added later.

## Acceptance behavior

A valid request is stored and receives an accepted response. A request with missing or invalid data is not stored and receives a response identifying the validation problem. Storage or server failures must not be reported as successful acceptance.

## API and validation

`POST /api/appointments` accepts JSON with exactly `name`, `email`, `preferredDate`, and `note`. Name is required (1–100 characters), email must match a basic address format and be at most 254 characters, preferredDate must be a real ISO `YYYY-MM-DD` calendar date, and note may be empty but is limited to 500 characters. Invalid JSON/size returns 400; invalid fields return 422 with `{ "error": "..." }`. Successful storage returns 201 with `{ "id": 1, "status": "accepted" }`. A storage error returns 500; it is never acknowledged as accepted.

## Run and test

The server uses only Python 3.10+ standard-library modules and SQLite. Run `python3 server.py` to start at `http://127.0.0.1:8000`. Set `PORT`, `HOST`, or `APPOINTMENTS_DB` to configure the listener or database file. SQLite creates the database and table automatically. Run tests from this directory with `python3 -m unittest -v`.

In development, Vite proxies `/api` to `http://127.0.0.1:8000`; set `VITE_API_PROXY` to change the proxy target. For a separately hosted frontend, set `VITE_API_BASE_URL` at build time to the API origin.
