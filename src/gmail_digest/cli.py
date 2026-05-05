from __future__ import annotations

import argparse
from pathlib import Path

from .classifier import HybridClassifier
from .config import AccountConfig, AppConfig, load_config
from .digest import DigestBuilder
from .gmail_client import GmailReadOnlyClient, SCOPES
from .html_preview import render_html_digest
from .preferences import PreferenceMemory
from .sender import DigestSender
from .storage import read_scan, write_classified, write_scan
from .whatsapp import build_whatsapp_message, build_whatsapp_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Gmail digest assistant.")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Fetch Gmail metadata/snippets read-only.")
    scan_parser.add_argument("--account", default=None, help="Account name from config.")
    scan_parser.add_argument("--mode", choices=["first", "daily"], default="daily")
    scan_parser.add_argument("--output", default=None)

    digest_parser = subparsers.add_parser("digest", help="Classify a scan and write digest text.")
    digest_parser.add_argument("--scan-file", required=True)
    digest_parser.add_argument("--account", default=None)
    digest_parser.add_argument("--output", default=None)

    send_parser = subparsers.add_parser("send", help="Send an existing digest text by email.")
    send_parser.add_argument("--digest-file", required=True)
    send_parser.add_argument("--subject", default="Gmail Digest")

    run_parser = subparsers.add_parser("run", help="Scan, classify, generate, and optionally send.")
    run_parser.add_argument("--account", default=None)
    run_parser.add_argument("--mode", choices=["first", "daily"], default="daily")
    run_parser.add_argument("--send", action="store_true")

    args = parser.parse_args()
    config = load_config(args.config)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "scan":
        account = _select_account(config, args.account)
        messages = _scan_account(config, account, args.mode)
        output = Path(args.output) if args.output else _scan_path(config, account.name)
        write_scan(output, messages)
        print(f"Wrote {len(messages)} messages to {output}")
        return

    if args.command == "digest":
        account_name = args.account or Path(args.scan_file).stem
        digest_text, digest_html, whatsapp_url, classified = _build_digest(
            config, Path(args.scan_file), account_name
        )
        output = Path(args.output) if args.output else _digest_path(config, account_name)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(digest_text, encoding="utf-8")
        _html_path(config, account_name).write_text(digest_html, encoding="utf-8")
        if whatsapp_url:
            _whatsapp_path(config, account_name).write_text(whatsapp_url, encoding="utf-8")
        write_classified(_classified_path(config, account_name), classified)
        print(f"Wrote digest to {output}")
        print(f"Wrote HTML preview to {_html_path(config, account_name)}")
        if whatsapp_url:
            print(f"Wrote WhatsApp preview link to {_whatsapp_path(config, account_name)}")
        return

    if args.command == "send":
        body = Path(args.digest_file).read_text(encoding="utf-8")
        DigestSender().send(
            to_email=config.digest.recipient_email,
            subject=args.subject,
            body=body,
        )
        print(f"Sent digest to {config.digest.recipient_email}")
        return

    if args.command == "run":
        accounts = [_select_account(config, args.account)] if args.account else config.gmail.accounts
        for account in accounts:
            messages = _scan_account(config, account, args.mode)
            scan_path = _scan_path(config, account.name)
            write_scan(scan_path, messages)
            digest_text, digest_html, whatsapp_url, classified = _build_digest(
                config, scan_path, account.name
            )
            digest_path = _digest_path(config, account.name)
            digest_path.parent.mkdir(parents=True, exist_ok=True)
            digest_path.write_text(digest_text, encoding="utf-8")
            _html_path(config, account.name).write_text(digest_html, encoding="utf-8")
            if whatsapp_url:
                _whatsapp_path(config, account.name).write_text(whatsapp_url, encoding="utf-8")
            write_classified(_classified_path(config, account.name), classified)
            if args.send:
                DigestSender().send(
                    to_email=config.digest.recipient_email,
                    subject=f"Gmail Digest: {account.name}",
                    body=digest_text,
                )
            print(f"Finished {account.name}: {len(messages)} messages, digest at {digest_path}")
        return


def _select_account(config: AppConfig, account_name: str | None) -> AccountConfig:
    if account_name is None:
        return config.gmail.accounts[0]
    for account in config.gmail.accounts:
        if account.name == account_name:
            return account
    raise ValueError(f"Unknown account {account_name!r}")


def _scan_account(config: AppConfig, account: AccountConfig, mode: str):
    _assert_read_only_scopes()
    days = config.scan.first_run_days if mode == "first" else config.scan.daily_days
    unread_days = config.scan.older_unread_days if mode == "first" else None
    client = GmailReadOnlyClient(config.gmail)
    return client.fetch_messages(
        account,
        days=days,
        unread_lookback_days=unread_days,
        max_results=config.scan.max_messages_per_account,
    )


def _build_digest(config: AppConfig, scan_file: Path, account_name: str):
    messages = read_scan(scan_file)
    preferences = PreferenceMemory.load(config.output_dir / "preferences.json")
    classified = HybridClassifier(preferences=preferences).classify_many(messages)
    builder = DigestBuilder(
        max_lines=config.digest.max_lines,
        cleanup_limit=config.digest.cleanup_suggestions_per_account,
    )
    content = builder.build_content(account_name, classified)
    whatsapp_url = None
    if config.whatsapp.phone_number:
        whatsapp_url = build_whatsapp_url(
            config.whatsapp.phone_number,
            build_whatsapp_message(content),
        )
    digest_text = builder.build_text(content)
    digest_html = render_html_digest(content, whatsapp_url=whatsapp_url)
    return digest_text, digest_html, whatsapp_url, classified


def _scan_path(config: AppConfig, account_name: str) -> Path:
    return config.output_dir / "scans" / f"{account_name}.json"


def _digest_path(config: AppConfig, account_name: str) -> Path:
    return config.output_dir / "digests" / f"{account_name}.txt"


def _html_path(config: AppConfig, account_name: str) -> Path:
    return config.output_dir / "digests" / f"{account_name}.html"


def _whatsapp_path(config: AppConfig, account_name: str) -> Path:
    return config.output_dir / "digests" / f"{account_name}.whatsapp.url"


def _classified_path(config: AppConfig, account_name: str) -> Path:
    return config.output_dir / "classified" / f"{account_name}.json"


def _assert_read_only_scopes() -> None:
    if SCOPES != ["https://www.googleapis.com/auth/gmail.readonly"]:
        raise RuntimeError("V1 must use Gmail read-only scope only.")
