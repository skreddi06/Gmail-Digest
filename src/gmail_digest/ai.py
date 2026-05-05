from __future__ import annotations

import os

from .models import Category, Classification, EmailMessage


class AIClassifier:
    def __init__(self, provider: str = "disabled", model: str = "gpt-4.1-mini"):
        self.provider = provider
        self.model = model

    @classmethod
    def from_env(cls) -> "AIClassifier":
        return cls(
            provider=os.getenv("AI_PROVIDER", "disabled").strip().lower(),
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        )

    def classify(self, message: EmailMessage) -> Classification | None:
        if self.provider in {"", "disabled", "none", "rules"}:
            return None
        if self.provider == "openai":
            return self._classify_with_openai(message)
        raise ValueError(f"Unsupported AI_PROVIDER: {self.provider}")

    def _classify_with_openai(self, message: EmailMessage) -> Classification | None:
        try:
            from openai import OpenAI
            from pydantic import BaseModel, Field
        except ImportError as exc:
            raise RuntimeError(
                "AI_PROVIDER=openai requires optional dependencies: python -m pip install -e '.[ai]'"
            ) from exc

        class EmailDecision(BaseModel):
            category: str = Field(description="One supported Gmail Digest category.")
            summary: str = Field(description="One-line useful summary.")
            reason: str = Field(description="Why this category was chosen.")
            needs_reply: bool = False
            money_related: bool = False
            security_related: bool = False
            cleanup_candidate: bool = False
            confidence: float = Field(ge=0, le=1)

        client = OpenAI()
        prompt = (
            "Classify this email for a read-only personal Gmail digest. "
            "Use one category exactly from: "
            f"{', '.join(category.value for category in Category)}. "
            "Treat business requests, bills, subscriptions, security alerts, government/legal/HR, "
            "and emails needing user action as important. Return concise fields only.\n\n"
            f"Account: {message.account_name} <{message.account_email}>\n"
            f"From: {message.sender} <{message.sender_email}>\n"
            f"Subject: {message.subject}\n"
            f"Snippet: {message.snippet}"
        )
        response = client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": "You classify emails for a safe read-only inbox digest. Never suggest destructive action.",
                },
                {"role": "user", "content": prompt},
            ],
            text_format=EmailDecision,
        )
        decision = response.output_parsed
        category = _coerce_category(decision.category)
        if category is None:
            return None
        return Classification(
            category=category,
            summary=decision.summary[:180],
            reason=decision.reason[:180],
            needs_reply=decision.needs_reply,
            money_related=decision.money_related,
            security_related=decision.security_related,
            cleanup_candidate=decision.cleanup_candidate,
            confidence=float(decision.confidence),
        )


def _coerce_category(value: str) -> Category | None:
    normalized = value.strip().lower()
    for category in Category:
        if category.value.lower() == normalized:
            return category
    return None
