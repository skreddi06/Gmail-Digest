from gmail_digest.digest import DigestBuilder
from gmail_digest.models import Category, ClassifiedEmail, Classification, EmailMessage


def classified(category: Category, *, sender_domain: str = "example.com") -> ClassifiedEmail:
    message = EmailMessage(
        id="1",
        thread_id="t1",
        account_name="primary",
        account_email="me@gmail.com",
        sender="Sender",
        sender_email=f"sender@{sender_domain}",
        sender_domain=sender_domain,
        subject="Test subject",
        date="2026-05-01T10:00:00+00:00",
        snippet="Snippet",
    )
    return ClassifiedEmail(
        message=message,
        classification=Classification(
            category=category,
            summary="Snippet",
            reason="Reason",
            needs_reply=category == Category.NEEDS_REPLY,
            money_related=category == Category.MONEY,
            security_related=category == Category.SECURITY,
            cleanup_candidate=category in {Category.MARKETING, Category.CLEANUP},
            confidence=0.8,
        ),
    )


def test_digest_contains_required_footer_and_sections():
    text = DigestBuilder(max_lines=25).build(
        "primary",
        [
            classified(Category.MONEY),
            classified(Category.NEEDS_REPLY),
            classified(Category.MARKETING, sender_domain="brand.com"),
        ],
    )
    assert "Summary:" in text
    assert "Important:" in text
    assert "Needs Reply:" in text
    assert "Money / Subscriptions / Security:" in text
    assert "Cleanup Suggestions:" in text
    assert text.endswith("No action was taken.")


def test_digest_preserves_sections_when_many_items_exist():
    text = DigestBuilder(max_lines=12).build(
        "primary",
        [classified(Category.NEEDS_REPLY) for _ in range(10)]
        + [classified(Category.MONEY) for _ in range(10)]
        + [classified(Category.MARKETING, sender_domain="brand.com") for _ in range(10)],
    )
    assert "Summary:" in text
    assert "Important:" in text
    assert "Needs Reply:" in text
    assert "Money / Subscriptions / Security:" in text
    assert "Cleanup Suggestions:" in text
    assert text.endswith("No action was taken.")
