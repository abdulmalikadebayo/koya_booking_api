# Koya Booking API

A clinic appointment booking API and a small web page that uses it. Built for Task 1 of the Koya Cohort 4 assessment, following the contract at https://koyaacademy.com/assessment-api/openapi.json.

- **API** (`server/`): Django 6 and Django REST Framework on Postgres.
- **Web page** (`frontend/`): React 19, TypeScript, Tailwind v4 and the BoardUI component library, built with Vite.

## Live

- API base URL: _add after deploy_
- Web page: _add after deploy_

## What it does

Patients see the available slots, book one, and get a confirmation. Every level of the assessment is implemented.

| Level | Behaviour |
|---|---|
| 1 | `POST /reset`, `GET /slots`, `POST /bookings`, `GET /bookings/{id}` |
| 2 | Every request needs the `X-API-Key` header (401 otherwise). Bookings with missing, empty or invalid fields are rejected (400), unknown slots return 404, and slots that already started return 400. Names and emails are trimmed and emails are stored in lower case. |
| 3 | A slot can only have one confirmed booking, even when many requests arrive at once (409 for the rest). `DELETE /bookings/{id}` cancels a booking and frees the slot. |
| 4 | `Idempotency-Key` makes retries safe. `GET /bookings?email=` pages through a person's bookings with a cursor. |
| 5 | At most 5 booking attempts per email per minute, failed attempts included. The 6th returns 429 with `Retry-After`. |

Every error response has the shape `{"error": "<message>"}`, including 401, 404, 405, 422 and 429.

## How it works

- **No double booking.** Booking runs in a transaction that locks the slot row, so simultaneous requests queue up and only the first succeeds. A partial unique index (one confirmed booking per slot) is the backstop, so the database refuses a duplicate even if the application code slipped.
- **Idempotency.** A table stores the key, a hash of the (trimmed) request body and the response. The same key and body replays the stored 201 with the same booking id. A different body returns 422. A Postgres advisory lock on the key makes two simultaneous identical requests create one booking. Only successful bookings are stored, so a retry after a failure (for example a slot that has since been freed) can still succeed.
- **Rate limit.** A table of attempts per email. Each request takes a per-email advisory lock, counts the attempts in the last 60 seconds and either records a new one or returns the seconds to wait. The email is trimmed and lower-cased first, so `ADA@x.com` and ` ada@x.com ` share one limit. Attempts without a valid email can't be attributed and aren't counted.
- **Paging.** The cursor encodes the position (created time and id) of the last item, so pages stay stable while bookings change. Bookings are listed oldest first.
- **`POST /reset`** deletes bookings, slots, stored idempotency records and rate-limit attempts, then loads the slots you send.

## Run it locally

You need Python 3.13, pipenv, Node 22 and Docker (for the test database).

**API**

```bash
cd server
pipenv install --dev
cp .env.template .env      # then fill in the values
make migrate
make run                   # http://localhost:8001
```

`.env` needs a `SECRET_KEY`, an `API_KEY` of your choosing, the `DB_*` connection settings for a Postgres database and `CORS_ALLOWED_ORIGINS` for the web page's origin. See [server/README.md](server/README.md).

**Web page**

```bash
cd frontend
npm install
cp .env.example .env.local   # set VITE_API_URL and VITE_API_KEY
npm run dev                  # http://localhost:5173
```

## Tests

```bash
cd server
make db      # starts a local Postgres in Docker
make test    # 93 tests, about 5 seconds
```

The tests run against Postgres, not SQLite, because the concurrency guarantees rely on row locks, a partial unique index and advisory locks. They include simultaneous booking, idempotency and rate-limit tests.

To check a running API against the whole contract:

```bash
python scripts/smoke.py <base_url> <api_key>
```

Warning: the script calls `POST /reset`, which wipes every booking and slot on that server.

## Project layout

```
server/
  src/config/            Django project (settings, urls, wsgi)
  src/booking/           the API
    api.py               views
    serializers.py       request validation and response shapes
    models.py            Slot, Booking, IdempotencyRecord, BookingAttempt
    auth.py              X-API-Key authentication
    errors.py            {"error": ...} responses
    idempotency.py       idempotency keys
    ratelimit.py         per-email rate limit
    pagination.py        opaque cursors
    tests/               one test module per level
frontend/
  src/api.ts             API client
  src/booking/           slot list, booking form, confirmation
  src/components/        BoardUI components (generated)
scripts/smoke.py         contract check against any base URL
```
