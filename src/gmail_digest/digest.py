from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import Category, ClassifiedEmail


@dataclass(frozen=True)
class DigestEntry:
    sender: str
    subject: str
    reason: str
    summary: str
    category: Category


@dataclass(frozen=True)
class CleanupSuggestion:
    domain: str
    count: int


@dataclass(frozen=True)
class DigestContent:
    account_name: str
    total_count: int
    important_count: int
    needs_reply_count: int
    money_security_count: int
    noise_count: int
    important: list[DigestEntry]
    needs_reply: list[DigestEntry]
    money_security: list[DigestEntry]
    cleanup: list[CleanupSuggestion]


class DigestBuilder:
    def __init__(self, max_lines: int = 25, cleanup_limit: int = 2):
        self.max_lines = max_lines
        self.cleanup_limit = cleanup_limit

    def build_content(self, account_name: str, emails: list[ClassifiedEmail]) -> DigestContent:
        counts = Counter(item.classification.category for item in emails)
        important_all = [
            item
            for item in emails
            if item.classification.category
            in {Category.IMPORTANT, Category.NEEDS_REPLY, Category.MONEY, Category.SECURITY, Category.OFFICIAL}
        ]
        needs_reply_all = [item for item in emails if item.classification.needs_reply]
        money_security_all = [
            item
            for item in emails
            if item.classification.money_related or item.classification.security_related
        ]
        cleanup_all = self._cleanup_suggestions(emails)
        return DigestContent(
            account_name=account_name,
            total_count=len(emails),
            important_count=len(important_all),
            needs_reply_count=len(needs_reply_all),
            money_security_count=len(money_security_all),
            noise_count=counts[Category.MARKETING] + counts[Category.LOW_VALUE] + counts[Category.CLEANUP],
            important=[_entry(item) for item in important_all[:3]],
            needs_reply=[_entry(item) for item in needs_reply_all[:2]],
            money_security=[_entry(item) for item in money_security_all[:2]],
            cleanup=[
                CleanupSuggestion(domain=domain, count=count)
                for domain, count in cleanup_all[: self.cleanup_limit]
            ],
        )

    def build(self, account_name: str, emails: list[ClassifiedEmail]) -> str:
        return self.build_text(self.build_content(account_name, emails))

    def build_text(self, content: DigestContent) -> str:
        lines = [
            f"{content.account_name} Morning Digest",
            "",
            "Summary:",
            (
                f"Scanned {content.total_count} emails. "
                f"{content.important_count} look important, {content.needs_reply_count} may need a reply, "
                f"and {content.money_security_count} are money/security related."
            ),
            (
                f"Noise check: {content.noise_count} "
                "marketing, newsletter, or low-value notifications found."
            ),
        ]

        self._append_section(lines, "Important:", content.important)
        self._append_section(lines, "Needs Reply:", content.needs_reply)
        self._append_section(lines, "Money / Subscriptions / Security:", content.money_security)

        lines.append("")
        lines.append("Cleanup Suggestions:")
        if content.cleanup:
            for item in content.cleanup:
                lines.append(f"- {item.domain}: {item.count} recent low-value or marketing emails")
        else:
            lines.append("- No obvious repeat cleanup sender today.")

        lines.append("")
        lines.append("No action was taken.")
        return "\n".join(self._trim(lines))

    def _append_section(self, lines: list[str], title: str, items: list[DigestEntry]) -> None:
        lines.append("")
        lines.append(title)
        if not items:
            lines.append("- None found.")
            return
        for item in items:
            lines.append(f"- {item.sender}: {item.subject}")
            reason = item.reason or item.summary
            if reason:
                lines.append(f"  Why: {reason}")

    def _trim(self, lines: list[str]) -> list[str]:
        if len(lines) <= self.max_lines:
            return lines
        required_headers = {
            "Summary:",
            "Important:",
            "Needs Reply:",
            "Money / Subscriptions / Security:",
            "Cleanup Suggestions:",
        }
        if not required_headers.issubset(set(lines)):
            return lines
        footer = "No action was taken."
        trimmed = lines[: self.max_lines - 2]
        if not required_headers.issubset(set(trimmed)):
            return lines
        if trimmed[-1] != "":
            trimmed.append("")
        trimmed.append(footer)
        return trimmed

    @staticmethod
    def _cleanup_suggestions(emails: list[ClassifiedEmail]) -> list[tuple[str, int]]:
        counts: defaultdict[str, int] = defaultdict(int)
        for item in emails:
            classification = item.classification
            domain = item.message.sender_domain or item.message.sender_email
            if domain and (
                classification.cleanup_candidate
                or classification.category
                in {Category.MARKETING, Category.LOW_VALUE, Category.CLEANUP}
            ):
                counts[domain] += 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _entry(item: ClassifiedEmail) -> DigestEntry:
    message = item.message
    classification = item.classification
    return DigestEntry(
        sender=message.sender,
        subject=message.subject,
        reason=classification.reason,
        summary=classification.summary,
        category=classification.category,
    )
