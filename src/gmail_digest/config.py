from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AccountConfig:
    name: str
    email: str


@dataclass(frozen=True)
class ScanConfig:
    first_run_days: int = 90
    daily_days: int = 1
    include_older_unread_for_first_days: int = 5
    older_unread_days: int = 90
    max_messages_per_account: int = 100


@dataclass(frozen=True)
class DigestConfig:
    recipient_email: str
    max_lines: int = 25
    cleanup_suggestions_per_account: int = 2


@dataclass(frozen=True)
class GmailConfig:
    client_secrets_file: Path
    token_dir: Path
    accounts: list[AccountConfig]


@dataclass(frozen=True)
class SenderConfig:
    provider: str = "smtp"


@dataclass(frozen=True)
class WhatsAppConfig:
    phone_number: str = ""


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    output_dir: Path
    scan: ScanConfig
    digest: DigestConfig
    gmail: GmailConfig
    sender: SenderConfig
    whatsapp: WhatsAppConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "Missing PyYAML. Install dependencies with: python -m pip install -e '.[dev]'"
        ) from exc

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {path}")
    return data


def load_config(path: str | Path) -> AppConfig:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    if load_dotenv:
        load_dotenv()
    config_path = Path(path)
    data = _read_yaml(config_path)

    app_data = data.get("app", {}) or {}
    scan_data = data.get("scan", {}) or {}
    digest_data = data.get("digest", {}) or {}
    gmail_data = data.get("gmail", {}) or {}
    sender_data = data.get("sender", {}) or {}
    whatsapp_data = data.get("whatsapp", {}) or {}

    accounts = [
        AccountConfig(name=str(item["name"]), email=str(item["email"]))
        for item in gmail_data.get("accounts", [])
    ]
    if not accounts:
        raise ValueError("At least one Gmail account is required in config.gmail.accounts")

    output_dir = Path(app_data.get("output_dir", ".local"))
    return AppConfig(
        timezone=str(app_data.get("timezone", "America/New_York")),
        output_dir=output_dir,
        scan=ScanConfig(
            first_run_days=int(scan_data.get("first_run_days", 90)),
            daily_days=int(scan_data.get("daily_days", 1)),
            include_older_unread_for_first_days=int(
                scan_data.get("include_older_unread_for_first_days", 5)
            ),
            older_unread_days=int(scan_data.get("older_unread_days", 90)),
            max_messages_per_account=int(scan_data.get("max_messages_per_account", 100)),
        ),
        digest=DigestConfig(
            recipient_email=str(digest_data.get("recipient_email", "")),
            max_lines=int(digest_data.get("max_lines", 25)),
            cleanup_suggestions_per_account=int(
                digest_data.get("cleanup_suggestions_per_account", 2)
            ),
        ),
        gmail=GmailConfig(
            client_secrets_file=Path(
                gmail_data.get("client_secrets_file", "credentials/google-oauth-client.json")
            ),
            token_dir=Path(gmail_data.get("token_dir", output_dir / "tokens")),
            accounts=accounts,
        ),
        sender=SenderConfig(provider=str(sender_data.get("provider", "smtp"))),
        whatsapp=WhatsAppConfig(phone_number=str(whatsapp_data.get("phone_number", ""))),
    )
