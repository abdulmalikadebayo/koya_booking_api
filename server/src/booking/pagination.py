import base64
import binascii
import json
from datetime import datetime


def encode_cursor(created_at: datetime, id: str) -> str:
    """Opaque position of the last item on a page."""
    raw = json.dumps([created_at.isoformat(), id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Inverse of encode_cursor. Raises ValueError for anything invalid."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        created_at, id = json.loads(base64.urlsafe_b64decode(padded.encode()))
        if not isinstance(id, str):
            raise ValueError("bad cursor")
        return datetime.fromisoformat(created_at), id
    except (binascii.Error, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
