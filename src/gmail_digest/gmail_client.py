from __future__ import annotations

from datetime import date, timedelta
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Any

from .config import AccountConfig, GmailConfig
from .models import EmailMessage

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SCOPES = [READ_ONLY_SCOPE]


class GmailReadOnlyClient:
    """Small wrapper around Gmail API that requests read-only access only."""

    def __init__(self, gmail_config: GmailConfig):
        self.gmail_config = gmail_config

    def fetch_messages(
        self,
        account: AccountConfig,
        *,
        days: int,
        unread_lookback_days: int | None = None,
        max_results: int = 100,
    ) -> list[EmailMessage]:
        service = self._build_service(account)
        queries = [self._after_query(days)]
        if unread_lookback_days:
            queries.append(f"is:unread {self._after_query(unread_lookback_days)}")

        messages: dict[str, EmailMessage] = {}
        for query in queries:
            for message_id in self._list_message_ids(service, query, max_results):
                raw = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message_id, format="metadata")
                    .execute()
                )
                parsed = self._parse_message(raw, account)
                messages[parsed.id] = parsed
        return sorted(messages.values(), key=lambda item: item.date, reverse=True)

    def _build_service(self, account: AccountConfig) -> Any:
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Missing Gmail dependencies. Run: python -m pip install -e ."
            ) from exc

        token_path = self.gmail_config.token_dir / f"{account.name}.json"
        credentials = None
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.gmail_config.client_secrets_file),
                    SCOPES,
                )
                credentials = flow.run_local_server(port=0)
            self._write_token(token_path, credentials.to_json())

        return build("gmail", "v1", credentials=credentials)

    @staticmethod
    def _write_token(path: Path, token_json: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token_json, encoding="utf-8")

    @staticmethod
    def _after_query(days: int) -> str:
        cutoff = date.today() - timedelta(days=days)
        return f"after:{cutoff.strftime('%Y/%m/%d')}"

    @staticmethod
    def _list_message_ids(service: Any, query: str, max_results: int) -> list[str]:
        found: list[str] = []
        request = service.users().messages().list(userId="me", q=query, maxResults=min(max_results, 100))
        while request is not None and len(found) < max_results:
            response = request.execute()
            found.extend(item["id"] for item in response.get("messages", []))
            if len(found) >= max_results:
                break
            request = service.users().messages().list_next(request, response)
        return found[:max_results]

    @classmethod
    def _parse_message(cls, raw: dict[str, Any], account: AccountConfig) -> EmailMessage:
        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in raw.get("payload", {}).get("headers", [])
        }
        sender_header = headers.get("from", "")
        sender_name, sender_email = cls._parse_sender(sender_header)
        parsed_date = cls._parse_date(headers.get("date", ""))
        labels = list(raw.get("labelIds", []))
        return EmailMessage(
            id=str(raw.get("id", "")),
            thread_id=str(raw.get("threadId", "")),
            account_name=account.name,
            account_email=account.email,
            sender=sender_name or sender_email or sender_header,
            sender_email=sender_email,
            sender_domain=sender_email.split("@")[-1].lower() if "@" in sender_email else "",
            subject=headers.get("subject", "(no subject)"),
            date=parsed_date,
            snippet=raw.get("snippet", ""),
            labels=labels,
            unread="UNREAD" in labels,
        )

    @staticmethod
    def _parse_sender(value: str) -> tuple[str, str]:
        parsed = getaddresses([value])
        if not parsed:
            return value, ""
        name, email = parsed[0]
        return name, email.lower()

    @staticmethod
    def _parse_date(value: str) -> str:
        if not value:
            return ""
        try:
            return parsedate_to_datetime(value).isoformat()
        except (TypeError, ValueError):
            return value
