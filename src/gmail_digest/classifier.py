from __future__ import annotations

import re
from collections.abc import Iterable

from .ai import AIClassifier
from .models import Category, ClassifiedEmail, Classification, EmailMessage
from .preferences import PreferenceMemory


MARKETING_TERMS = {
    "$",
    "% off",
    "advertisement",
    "black friday",
    "coupon",
    "daily digest",
    "deal",
    "deals",
    "discount",
    "event tickets",
    "exclusive offer",
    "free shipping",
    "handpicked deals",
    "limited available",
    "limited time",
    "marketing",
    "memorial day",
    "newsletter",
    "offer",
    "promo",
    "promotion",
    "unsubscribe",
    "webinar",
    "you're gonna want",
}
MONEY_TERMS = {
    "autopay",
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
    "expires",
    "expired",
    "past due",
    "plan",
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
    "do you have",
    "follow up",
    "get back to me",
    "i need",
    "let me know",
    "need your",
    "please confirm",
    "please review",
    "please send",
    "please share",
    "reply",
    "respond",
    "response needed",
    "waiting on you",
    "your approval",
    "your input",
}
LOW_VALUE_SENDERS = {"no-reply", "noreply", "notification", "updates"}
HUMAN_ACTION_TERMS = {
    "call",
    "confirm",
    "deadline",
    "meeting",
    "request",
    "review",
    "schedule",
    "sent you",
    "shared with you",
    "waiting",
}


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
                priority_score=90,
            )

        if message.sender_domain in self.preferences.cleanup_domains:
            return Classification(
                category=Category.CLEANUP,
                summary=_summary(message),
                reason="Sender domain is saved as a cleanup candidate.",
                cleanup_candidate=True,
                confidence=0.95,
                priority_score=10,
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
        is_marketing = _looks_marketing(message, text)
        is_automated = _is_automated_sender(sender_local)

        if _has_any(text, SECURITY_TERMS):
            return Classification(
                category=Category.SECURITY,
                summary=_summary(message),
                reason="Account or security activity may need review.",
                security_related=True,
                confidence=0.85,
                priority_score=95,
            )

        if _has_any(text, MONEY_TERMS):
            return Classification(
                category=Category.MONEY,
                summary=_summary(message),
                reason="Payment, billing, subscription, or renewal signal.",
                money_related=True,
                confidence=0.82,
                priority_score=88,
            )

        if _has_any(text, OFFICIAL_TERMS):
            return Classification(
                category=Category.OFFICIAL,
                summary=_summary(message),
                reason="Official, HR, legal, payroll, benefit, or tax signal.",
                confidence=0.8,
                priority_score=84,
            )

        if is_marketing:
            return Classification(
                category=Category.MARKETING,
                summary=_summary(message),
                reason="Promotional or newsletter-style email.",
                cleanup_candidate=True,
                confidence=0.82,
                priority_score=12,
            )

        if self._needs_reply(message, text, is_automated):
            return Classification(
                category=Category.NEEDS_REPLY,
                summary=_summary(message),
                reason="Direct request or response likely needed.",
                needs_reply=True,
                confidence=0.78,
                priority_score=86,
            )

        if self._maybe_important(message, text, is_automated):
            return Classification(
                category=Category.MAYBE,
                summary=_summary(message),
                reason="Could matter, but needs user review before promoting.",
                confidence=0.58,
                priority_score=52,
            )

        if is_automated:
            return Classification(
                category=Category.LOW_VALUE,
                summary=_summary(message),
                reason="Automated notification sender with no strong action signal.",
                cleanup_candidate=True,
                confidence=0.68,
                priority_score=18,
            )

        return Classification(
            category=Category.UNSURE,
            summary=_summary(message),
            reason="No strong rule matched.",
            confidence=0.45,
            priority_score=30,
        )

    @staticmethod
    def _needs_reply(message: EmailMessage, text: str, is_automated: bool) -> bool:
        if is_automated:
            return False
        if _has_any(text, REPLY_TERMS):
            return True
        if "?" in message.subject and _has_any(text, HUMAN_ACTION_TERMS):
            return True
        return False

    @staticmethod
    def _maybe_important(message: EmailMessage, text: str, is_automated: bool) -> bool:
        if is_automated:
            return False
        if message.unread and _has_any(text, HUMAN_ACTION_TERMS | {"important", "urgent"}):
            return True
        if _has_any(text, {"application", "interview", "job", "offer letter", "document", "appointment"}):
            return True
        return False


def _search_text(message: EmailMessage) -> str:
    return f"{message.sender} {message.sender_email} {message.subject} {message.snippet}".lower()


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _looks_marketing(message: EmailMessage, text: str) -> bool:
    if _has_any(text, MARKETING_TERMS):
        return True
    subject = message.subject.lower()
    if re.search(r"\b\d+%|\$\d+|\b\d+\s*for\s*\$\d+", subject):
        return True
    return False


def _is_automated_sender(sender_local: str) -> bool:
    return any(marker in sender_local for marker in LOW_VALUE_SENDERS)


def _summary(message: EmailMessage) -> str:
    normalized = re.sub(r"\s+", " ", message.snippet).strip()
    if normalized:
        return normalized[:180]
    return message.subject[:180]
