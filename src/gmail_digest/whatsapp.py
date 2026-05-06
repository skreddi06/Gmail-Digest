from __future__ import annotations

import re
from urllib.parse import quote

from .digest import DigestContent


def normalize_whatsapp_number(value: str) -> str:
    number = re.sub(r"\D", "", value)
    if not number:
        raise ValueError("WhatsApp phone number is empty.")
    return number


def build_whatsapp_message(content: DigestContent) -> str:
    lines = [
        f"{content.account_name} Morning Digest",
        (
            f"Scanned {content.total_count}. Important: {content.important_count}. "
            f"Needs reply: {content.needs_reply_count}. Money/security: {content.money_security_count}. "
            f"Maybe: {content.maybe_count}."
        ),
    ]
    if content.needs_reply:
        lines.append("Needs reply:")
        for item in content.needs_reply[:2]:
            lines.append(f"- {item.sender}: {item.subject}")
    if content.important:
        lines.append("Top important:")
        for item in content.important[:2]:
            lines.append(f"- {item.sender}: {item.subject}")
    if content.maybe_important:
        lines.append("Maybe important:")
        for item in content.maybe_important[:2]:
            lines.append(f"- {item.sender}: {item.subject}")
    if content.cleanup:
        lines.append("Cleanup:")
        for item in content.cleanup[:2]:
            lines.append(f"- {item.domain}: {item.count} low-value emails")
    lines.append("No action was taken.")
    return "\n".join(lines)


def build_whatsapp_url(number: str, message: str) -> str:
    normalized = normalize_whatsapp_number(number)
    return f"https://wa.me/{normalized}?text={quote(message)}"
