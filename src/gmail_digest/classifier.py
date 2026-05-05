from __future__ import annotations

import re
from collections.abc import Iterable

from .ai import AIClassifier
from .models import Category, ClassifiedEmail, Classification, EmailMessage
from .preferences import PreferenceMemory


MARKETING_TERMS = {
    "unsubscribe",
    "sale",
    "discount",
    "limited time",
    "newsletter",
    "promotion",
    "promo",
    "deal",
    "offer",
    "webinar",
}
MONEY_TERMS = {
    "invoice",
    "receipt",
    "payment",
    "paid",
    "subscription",
    "renewal",
    "renew",
    "billing",
    "bill",
    "charge",
    "failed payment",
    "statement",
    "refund",
}
SECURITY_TERMS = {
    "security alert",
    "new sign-in",
    "login",
    "password",
    "verification code",
    "2fa",
    "two-factor",
    "suspicious",
    "account alert",
}
OFFICIAL_TERMS = {
    "irs",
    "uscis",
    "government",
    "legal",
    "court",
    "benefits",
    "hr",
    "payroll",
    "w2",
    "w-2",
    "tax",
}
REPLY_TERMS = {
    "can you",
    "could you",
    "please",
    "question",
    "reply",
    "respond",
    "confirm",
    "let me know",
    "follow up",
    "needed",
}
LOW_VALUE_SENDERS = {"no-reply", "noreply", "notification", "updates"}


class HybridClassifier:
    def __init__(self, preferences: PreferenceMemory | None = None, ai: AIClassifier | None = None):
        self.preferences = preferences or PreferenceMemory()
        self.ai = ai or AIClassifier.from_env()

    def classify_many(self, messages: Iterable[EmailMessage]) -> list[ClassifiedEmail]:
        return [ClassifiedEmail(message, self.classify(message)) for message in messages]

    def classify(self, message: EmailMessage) -> Classification:
        override = self.preferences.category_overrides.get(message.sender_email)
        if override:
            return Classification(
                category=override,
                summary=_summary(message),
                reason="Matched a saved sender preference.",
                confidence=0.95,
            )

        if message.sender_domain in self.preferences.important_domains:
            return Classification(
                category=Category.IMPORTANT,
                summary=_summary(message),
                reason="Sender domain is saved as important.",
                confidence=0.95,
            )

        if message.sender_domain in self.preferences.cleanup_domains:
            return Classification(
                category=Category.CLEANUP,
                summary=_summary(message),
                reason="Sender domain is saved as a cleanup candidate.",
                cleanup_candidate=True,
                confidence=0.95,
            )

        rule_result = self._classify_with_rules(message)
        if rule_result.category not in {Category.UNSURE, Category.IMPORTANT}:
            return rule_result

        ai_result = self.ai.classify(message)
        if ai_result and ai_result.confidence >= 0.55:
            return ai_result
        return rule_result

    def _classify_with_rules(self, message: EmailMessage) -> Classification:
        text = _search_text(message)
        sender_local = message.sender_email.split("@")[0] if "@" in message.sender_email else ""

        if _has_any(text, SECURITY_TERMS):
            return Classification(
                category=Category.SECURITY,
                summary=_summary(message),
                reason="Contains security/account alert language.",
                security_related=True,
                confidence=0.85,
            )

        if _has_any(text, MONEY_TERMS):
            return Classification(
                category=Category.MONEY,
                summary=_summary(message),
                reason="Contains billing, payment, subscription, or renewal language.",
                money_related=True,
                confidence=0.82,
            )

        if _has_any(text, OFFICIAL_TERMS):
            return Classification(
                category=Category.OFFICIAL,
                summary=_summary(message),
                reason="Looks related to government, legal, company, HR, payroll, or tax.",
                confidence=0.8,
            )

        if _has_any(text, REPLY_TERMS) or "?" in message.subject:
            return Classification(
                category=Category.NEEDS_REPLY,
                summary=_summary(message),
                reason="Appears to ask for a response or action.",
                needs_reply=True,
                confidence=0.72,
            )

        if _has_any(text, MARKETING_TERMS):
            return Classification(
                category=Category.MARKETING,
                summary=_summary(message),
                reason="Contains marketing/newsletter language.",
                cleanup_candidate=True,
                confidence=0.78,
            )

        if any(marker in sender_local for marker in LOW_VALUE_SENDERS):
            return Classification(
                category=Category.LOW_VALUE,
                summary=_summary(message),
                reason="Automated notification sender.",
                cleanup_candidate=True,
                confidence=0.68,
            )

        return Classification(
            category=Category.UNSURE,
            summary=_summary(message),
            reason="No strong rule matched.",
            confidence=0.45,
        )


def _search_text(message: EmailMessage) -> str:
    return f"{message.sender} {message.sender_email} {message.subject} {message.snippet}".lower()


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _summary(message: EmailMessage) -> str:
    normalized = re.sub(r"\s+", " ", message.snippet).strip()
    if normalized:
        return normalized[:180]
    return message.subject[:180]
