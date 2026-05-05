import json

from gmail_digest.preferences import PreferenceMemory


def test_preference_memory_does_not_store_email_bodies(tmp_path):
    path = tmp_path / "preferences.json"
    memory = PreferenceMemory(
        important_domains={"bank.com"},
        cleanup_domains={"brand.com"},
        ignored_domains={"noise.com"},
    )
    memory.save(path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "body" not in json.dumps(saved).lower()
    assert "snippet" not in json.dumps(saved).lower()
    assert saved["important_domains"] == ["bank.com"]
