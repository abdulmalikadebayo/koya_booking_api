import hashlib
import json

from django.db import connection

from .models import IdempotencyRecord


def body_hash(data) -> str:
    """Hash of the request body after trimming, so equivalent retries match."""
    if isinstance(data, dict):
        data = {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}
        if isinstance(data.get("email"), str):
            data["email"] = data["email"].lower()
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def acquire_key_lock(key: str) -> None:
    """Serialise requests that share a key. Must run inside a transaction."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [f"idem:{key}"])


def find(key: str):
    return IdempotencyRecord.objects.filter(key=key).first()


def store(key: str, body_hash: str, status_code: int, response: dict) -> None:
    IdempotencyRecord.objects.create(
        key=key, body_hash=body_hash, status_code=status_code, response=response
    )
