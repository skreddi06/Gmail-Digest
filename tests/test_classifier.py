from gmail_digest.classifier import HybridClassifier
from gmail_digest.models import Category, EmailMessage


def message(subject: str, snippet: str = "", sender: str = "sender@example.com") -> EmailMessage:
    return EmailMessage(
        id="1",
        thread_id="t1",
        account_name="primary",
        account_email="me@gmail.com",
        sender=sender,
        sender_email=sender,
        sender_domain=sender.split("@")[-1],
        subject=subject,
        date="2026-05-01T10:00:00+00:00",
        snippet=snippet,
        labels=[],
        unread=False,
    )


def test_money_email_is_detected():
    result = HybridClassifier().classify(message("Your subscription renewal", "Payment due tomorrow"))
    assert result.category == Category.MONEY
    assert result.money_related is True


def test_needs_reply_is_detected():
    result = HybridClassifier().classify(message("Can you confirm?", "Please let me know."))
    assert result.category == Category.NEEDS_REPLY
    assert result.needs_reply is True


def test_marketing_email_is_cleanup_candidate():
    result = HybridClassifier().classify(message("Limited time sale", "Unsubscribe from this newsletter"))
    assert result.category == Category.MARKETING
    assert result.cleanup_candidate is True
