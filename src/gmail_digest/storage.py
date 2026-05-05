from __future__ import annotations

import json
from pathlib import Path

from .models import ClassifiedEmail, EmailMessage, utc_now_iso


def write_scan(path: Path, messages: list[EmailMessage]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": utc_now_iso(),
        "messages": [message.to_dict() for message in messages],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_scan(path: Path) -> list[EmailMessage]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EmailMessage.from_dict(item) for item in payload.get("messages", [])]


def write_classified(path: Path, emails: list[ClassifiedEmail]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": utc_now_iso(),
        "emails": [email.to_dict() for email in emails],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
