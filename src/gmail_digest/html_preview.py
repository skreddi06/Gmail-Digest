from __future__ import annotations

from html import escape

from .digest import CleanupSuggestion, DigestContent, DigestEntry


def render_html_digest(content: DigestContent, *, whatsapp_url: str | None = None) -> str:
    button = ""
    if whatsapp_url:
        button = (
            '<a href="'
            + escape(whatsapp_url, quote=True)
            + '" style="display:inline-block;padding:12px 16px;border-radius:8px;'
            + "background:#111827;color:#ffffff;text-decoration:none;font-weight:700;"
            + 'font-size:14px;">Open WhatsApp preview</a>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(content.account_name)} Morning Digest</title>
</head>
<body style="margin:0;background:#f6f7f9;color:#111827;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;line-height:1.45;">
  <div style="max-width:720px;margin:0 auto;padding:32px 18px;">
    <div style="padding:28px 28px 22px;background:#ffffff;border:1px solid #e6e8eb;border-radius:10px;">
      <p style="margin:0 0 8px;color:#6b7280;font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;">Gmail Digest</p>
      <h1 style="margin:0;color:#111827;font-size:28px;line-height:1.15;font-weight:750;">{escape(content.account_name)} Morning Digest</h1>
      <p style="margin:12px 0 0;color:#4b5563;font-size:15px;">A concise read-only scan of what needs your attention. No action was taken.</p>
      <div style="margin-top:22px;display:block;">
        {_stat_chip("Scanned", str(content.total_count))}
        {_stat_chip("Important", str(content.important_count))}
        {_stat_chip("Needs reply", str(content.needs_reply_count))}
        {_stat_chip("Money/Security", str(content.money_security_count))}
        {_stat_chip("Noise", str(content.noise_count))}
      </div>
      {_action_row(button)}
    </div>

    {_section("Important", "Highest-signal emails from this scan.", content.important)}
    {_section("Needs Reply", "Messages that may need your response.", content.needs_reply)}
    {_section("Money / Subscriptions / Security", "Bills, subscriptions, renewals, payments, or account alerts.", content.money_security)}
    {_cleanup_section(content.cleanup)}

    <p style="margin:22px 0 0;text-align:center;color:#6b7280;font-size:13px;">No action was taken.</p>
  </div>
</body>
</html>
"""


def _stat_chip(label: str, value: str) -> str:
    return (
        '<span style="display:inline-block;margin:0 8px 8px 0;padding:9px 11px;'
        + 'border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;">'
        + f'<span style="display:block;color:#6b7280;font-size:12px;">{escape(label)}</span>'
        + f'<span style="display:block;color:#111827;font-size:18px;font-weight:750;">{escape(value)}</span>'
        + "</span>"
    )


def _action_row(button: str) -> str:
    if not button:
        return ""
    return f'<div style="margin-top:18px;">{button}</div>'


def _section(title: str, subtitle: str, items: list[DigestEntry]) -> str:
    body = _empty_item()
    if items:
        body = "".join(_entry_card(item) for item in items)
    return f"""
    <div style="margin-top:18px;padding:22px 24px;background:#ffffff;border:1px solid #e6e8eb;border-radius:10px;">
      <h2 style="margin:0;color:#111827;font-size:18px;line-height:1.25;">{escape(title)}</h2>
      <p style="margin:6px 0 16px;color:#6b7280;font-size:14px;">{escape(subtitle)}</p>
      {body}
    </div>
"""


def _entry_card(item: DigestEntry) -> str:
    reason = item.reason or item.summary or "Flagged for review."
    return f"""
      <div style="padding:14px 0;border-top:1px solid #eef0f2;">
        <p style="margin:0 0 4px;color:#111827;font-size:15px;font-weight:700;">{escape(item.sender)}</p>
        <p style="margin:0;color:#111827;font-size:14px;">{escape(item.subject)}</p>
        <p style="margin:7px 0 0;color:#6b7280;font-size:13px;">{escape(reason)}</p>
      </div>
"""


def _cleanup_section(items: list[CleanupSuggestion]) -> str:
    if items:
        body = "".join(
            f"""
      <div style="padding:12px 0;border-top:1px solid #eef0f2;">
        <p style="margin:0;color:#111827;font-size:15px;font-weight:700;">{escape(item.domain)}</p>
        <p style="margin:5px 0 0;color:#6b7280;font-size:13px;">{item.count} recent low-value or marketing emails.</p>
      </div>
"""
            for item in items
        )
    else:
        body = _empty_item("No obvious repeat cleanup sender today.")
    return f"""
    <div style="margin-top:18px;padding:22px 24px;background:#ffffff;border:1px solid #e6e8eb;border-radius:10px;">
      <h2 style="margin:0;color:#111827;font-size:18px;line-height:1.25;">Cleanup Suggestions</h2>
      <p style="margin:6px 0 16px;color:#6b7280;font-size:14px;">Repeat marketing or newsletter sources worth reviewing.</p>
      {body}
    </div>
"""


def _empty_item(text: str = "None found.") -> str:
    return (
        '<div style="padding:14px 0;border-top:1px solid #eef0f2;">'
        + f'<p style="margin:0;color:#6b7280;font-size:14px;">{escape(text)}</p>'
        + "</div>"
    )
