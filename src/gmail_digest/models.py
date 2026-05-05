from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class Category(StrEnum):
    IMPORTANT = "Important"
    NEEDS_REPLY = "Needs Reply"
    MONEY = "Money / Bills / Subscriptions"
    SECURITY = "Security / Account Alert"
    OFFICIAL = "Government / Legal / Company / HR"
    MARKETING = "Marketing / Newsletter"
    LOW_VALUE = "Low-Value Notification"
    CLEANUP = "Cleanup Candidate"
    UNSURE = "Unsure"


@dataclass(frozen=True)
class EmailMessage:
    id: str
    thread_id: str
    account_name: str
    account_email: str
    sender: str
    sender_email: str
    sender_domain: str
    subject: str
    date: str
    snippet: str
    labels: list[str] = field(default_factory=list)
    unread: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmailMessage":
        return cls(
            id=str(data.get("id", "")),
            thread_id=str(data.get("thread_id", "")),
            account_name=str(data.get("account_name", "")),
            account_email=str(data.get("account_email", "")),
            sender=str(data.get("sender", "")),
            sender_email=str(data.get("sender_email", "")),
            sender_domain=str(data.get("sender_domain", "")),
            subject=str(data.get("subject", "")),
            date=str(data.get("date", "")),
            snippet=str(data.get("snippet", "")),
            labels=list(data.get("labels", [])),
            unread=bool(data.get("unread", False)),
        )


@dataclass(frozen=True)
class Classification:
    category: Category
    summary: str
    reason: str
    needs_reply: bool = False
    money_related: bool = False
    security_related: bool = False
    cleanup_candidate: bool = False
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data


@dataclass(frozen=True)
class ClassifiedEmail:
    message: EmailMessage
    classification: Classification

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "classification": self.classification.to_dict(),
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
