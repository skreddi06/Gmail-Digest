from gmail_digest.digest import DigestBuilder
from gmail_digest.html_preview import render_html_digest
from gmail_digest.models import Category
from tests.test_digest import classified


def test_html_preview_contains_required_sections_and_footer():
    content = DigestBuilder(max_lines=25).build_content(
        "primary",
        [
            classified(Category.MONEY),
            classified(Category.NEEDS_REPLY),
            classified(Category.MARKETING, sender_domain="brand.com"),
        ],
    )
    html = render_html_digest(content, whatsapp_url="https://wa.me/15550102030?text=Hello")
    assert "primary Morning Digest" in html
    assert "Important" in html
    assert "Needs Reply" in html
    assert "Money / Subscriptions / Security" in html
    assert "Cleanup Suggestions" in html
    assert "No action was taken." in html
    assert "Open WhatsApp preview" in html
