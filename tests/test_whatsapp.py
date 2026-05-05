from gmail_digest.digest import DigestBuilder
from gmail_digest.models import Category
from gmail_digest.whatsapp import build_whatsapp_message, build_whatsapp_url, normalize_whatsapp_number
from tests.test_digest import classified


def test_whatsapp_number_is_digits_only():
    assert normalize_whatsapp_number("+1 (555) 010-2030") == "15550102030"


def test_whatsapp_url_is_encoded():
    content = DigestBuilder().build_content("primary", [classified(Category.NEEDS_REPLY)])
    message = build_whatsapp_message(content)
    url = build_whatsapp_url("+1 (555) 010-2030", message)
    assert url.startswith("https://wa.me/15550102030?text=")
    assert " " not in url
    assert "%0A" in url
