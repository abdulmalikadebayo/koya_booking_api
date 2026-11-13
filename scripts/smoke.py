"""End-to-end contract check for the clinic booking API.

Usage:  python scripts/smoke.py <base_url> <api_key>
        (or set API_KEY instead of passing the key)

WARNING: this calls POST /reset, which deletes every booking and slot on the
target. Only point it at a database you are happy to wipe.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8001"
KEY = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("API_KEY", "")

failures = []


def call(method, path, body=None, headers=None, key=KEY):
    """Returns (status, json_body, response_headers)."""
    request_headers = {"Content-Type": "application/json"}
    if key is not None:
        request_headers["X-API-Key"] = key
    request_headers.update(headers or {})
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method=method, headers=request_headers
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response), response.headers
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {"_raw": raw.decode(errors="replace")[:200]}
        return error.code, parsed, error.headers


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f"  -> {detail}"))
    if not condition:
        failures.append(name)


def is_error(body):
    return isinstance(body, dict) and set(body) == {"error"} and isinstance(body["error"], str)


def slot(id, hour, minute=0, provider="Dr Ade", day=10):
    start = f"2099-12-{day:02d}T{hour:02d}:{minute:02d}:00Z"
    end = f"2099-12-{day:02d}T{hour:02d}:{minute + 30:02d}:00Z"
    return {"id": id, "provider": provider, "start": start, "end": end}


def email(label):
    return f"{label}-{uuid.uuid4().hex[:8]}@example.com"


def book(slot_id, mail, name="Ada Obi", headers=None):
    return call("POST", "/bookings", {"slot_id": slot_id, "name": name, "email": mail}, headers)


def main():
    print(f"Target: {BASE}\n")

    # ---- Level 2: API key
    status, body, _ = call("GET", "/slots", key=None)
    check("L2 missing key -> 401 {error}", status == 401 and is_error(body), (status, body))
    status, body, _ = call("GET", "/slots", key="definitely-wrong")
    check("L2 wrong key -> 401 {error}", status == 401 and is_error(body), (status, body))
    status, body, _ = call("POST", "/reset", {"slots": []}, key=None)
    check("L2 /reset also needs the key", status == 401, status)

    # ---- Level 1: reset and slots
    slots = [
        slot("s3", 11, provider="Dr Bola"),
        slot("s1", 9),
        slot("s2", 10),
        slot("s4", 12),
        slot("s5", 13),
        slot("s6", 14),
        slot("s7", 15),
        {"id": "past", "provider": "Dr Ade", "start": "2001-01-01T09:00:00Z", "end": "2001-01-01T09:30:00Z"},
    ]
    status, body, _ = call("POST", "/reset", {"slots": slots})
    check("L1 reset -> 200", status == 200, (status, body))
    status, body, _ = call("GET", "/slots")
    listed = body.get("slots", []) if isinstance(body, dict) else []
    check("L1 slots 200 with {slots: [...]}", status == 200 and len(listed) == 8, (status, body))
    starts = [s["start"] for s in listed]
    check("L1 slots earliest start first", starts == sorted(starts), starts)
    check(
        "L1 slot fields id/provider/start/end/available",
        bool(listed) and all(set(s) == {"id", "provider", "start", "end", "available"} for s in listed),
        listed[:1],
    )
    check("L1 all slots available", all(s["available"] for s in listed))
    _, body, _ = call("GET", "/slots?provider=Dr%20Bola")
    check("L1 provider filter (exact)", [s["id"] for s in body["slots"]] == ["s3"], body)

    # ---- Level 1: book + get
    ada = email("ada")
    status, booking, _ = book("s1", ada)
    check("L1 book -> 201", status == 201, (status, booking))
    fields = {"id", "slot_id", "name", "email", "status", "created_at"}
    check("L1 booking fields", isinstance(booking, dict) and set(booking) == fields, booking)
    check("L1 status confirmed", booking.get("status") == "confirmed", booking)
    check(
        "L1 created_at ISO date-time",
        bool(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", booking.get("created_at", ""))),
        booking.get("created_at"),
    )
    status, got, _ = call("GET", f"/bookings/{booking['id']}")
    check("L1 get booking -> 200 same body", status == 200 and got == booking, (status, got))
    status, body, _ = call("GET", "/bookings/does-not-exist")
    check("L1 unknown booking -> 404 {error}", status == 404 and is_error(body), (status, body))
    _, body, _ = call("GET", "/slots")
    avail = {s["id"]: s["available"] for s in body["slots"]}
    check("L1 booked slot available=false", avail["s1"] is False and avail["s2"] is True, avail)

    # ---- Level 2: validation
    mail = email("val")
    for field in ("slot_id", "name", "email"):
        payload = {"slot_id": "s2", "name": "Ada", "email": mail}
        payload.pop(field)
        status, body, _ = call("POST", "/bookings", payload)
        check(f"L2 missing {field} -> 400", status == 400 and is_error(body), (status, body))
    status, body, _ = book("s2", email("e"), name="   ")
    check("L2 blank name -> 400", status == 400, (status, body))
    status, body, _ = book("s2", "not-an-email")
    check("L2 invalid email -> 400", status == 400 and is_error(body), (status, body))
    status, body, _ = book("nope", email("e"))
    check("L2 unknown slot -> 404 {error}", status == 404 and is_error(body), (status, body))
    status, body, _ = book("past", email("e"))
    check("L2 slot already started -> 400", status == 400 and is_error(body), (status, body))
    messy = email("Trim").upper().replace("@EXAMPLE.COM", "@Example.com")
    status, body, _ = book("s7", f"  {messy}  ", name="  Ada Obi  ")
    check(
        "L2 name/email trimmed, email lower-cased",
        status == 201 and body.get("name") == "Ada Obi" and body.get("email") == messy.lower(),
        (status, body),
    )

    # ---- Level 3: no double booking
    status, body, _ = book("s1", email("late"))
    check("L3 booked slot -> 409 {error}", status == 409 and is_error(body), (status, body))

    def race(i):
        return book("s2", email(f"race{i}"))[0]

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(race, range(10)))
    check("L3 10 simultaneous bookings -> exactly one 201", sorted(codes) == [201] + [409] * 9, sorted(codes))

    status, cancelled, _ = call("DELETE", f"/bookings/{booking['id']}")
    check("L3 cancel -> 200 status cancelled", status == 200 and cancelled.get("status") == "cancelled", (status, cancelled))
    status, body, _ = call("DELETE", f"/bookings/{booking['id']}")
    check("L3 cancel twice -> 409", status == 409 and is_error(body), (status, body))
    status, body, _ = call("DELETE", "/bookings/does-not-exist")
    check("L3 cancel unknown -> 404", status == 404 and is_error(body), (status, body))
    _, body, _ = call("GET", "/slots")
    check("L3 cancel frees the slot", {s["id"]: s["available"] for s in body["slots"]}["s1"] is True)
    status, body, _ = book("s1", email("again"))
    check("L3 freed slot can be booked again", status == 201, (status, body))

    # ---- Level 4: idempotency
    mail = email("idem")
    headers = {"Idempotency-Key": uuid.uuid4().hex}
    first = book("s4", mail, headers=headers)
    second = book("s4", mail, headers=headers)
    check(
        "L4 same key + body -> same status and booking id",
        first[0] == second[0] == 201 and first[1].get("id") == second[1].get("id"),
        (first[:2], second[:2]),
    )
    status, body, _ = book("s4", email("other"), headers=headers)
    check("L4 same key, different body -> 422", status == 422 and is_error(body), (status, body))
    _, listed_all, _ = call("GET", f"/bookings?email={mail}")
    check("L4 replay created no duplicate", len(listed_all.get("bookings", [])) == 1, listed_all)

    # ---- Level 4: paging
    mail = email("page")
    ids = [book(s, mail)[1]["id"] for s in ("s3", "s5", "s6")]
    seen, cursor, pages = [], None, 0
    while pages < 10:
        query = f"/bookings?email={mail.upper()}&limit=2" + (f"&cursor={cursor}" if cursor else "")
        status, body, _ = call("GET", query)
        if status != 200:
            break
        seen += [b["id"] for b in body["bookings"]]
        pages += 1
        cursor = body.get("next_cursor")
        if cursor is None:
            break
    check("L4 paging: oldest first, every booking once, last page null cursor", seen == ids and pages == 2, (seen, ids, pages))
    for bad in ("0", "51", "abc"):
        status, body, _ = call("GET", f"/bookings?email={mail}&limit={bad}")
        check(f"L4 limit={bad} -> 400", status == 400 and is_error(body), (status, body))

    # ---- Level 5: rate limit
    mail = email("rate")
    codes = [book("nope", mail)[0] for _ in range(5)]
    check("L5 first 5 attempts (failed ones count) are not limited", codes == [404] * 5, codes)
    status, body, response_headers = book("nope", mail)
    retry = response_headers.get("Retry-After")
    check("L5 6th attempt -> 429 {error}", status == 429 and is_error(body), (status, body))
    check("L5 Retry-After is whole seconds", bool(retry) and retry.isdigit() and int(retry) >= 1, retry)
    status, body, _ = book("nope", email("fresh"))
    check("L5 other emails unaffected", status == 404, (status, body))

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("All checks passed")


if __name__ == "__main__":
    main()
