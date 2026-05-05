# Gmail Digest Assistant

Read-only Gmail assistant that scans Gmail, classifies important messages, and sends a concise morning digest.

V1 safety promise: this app never deletes, archives, labels, replies, unsubscribes, or modifies Gmail. It requests only Gmail read-only access and sends the digest through a separate sender configuration.

## What V1 Does

- Connects to Gmail with `https://www.googleapis.com/auth/gmail.readonly`.
- Starts with one Gmail account, then supports multiple accounts in `config.yaml`.
- Scans the last 90 days for the first run.
- Scans yesterday's emails for daily runs.
- Classifies emails into important, needs reply, money/subscriptions, security, official/HR/legal, marketing/newsletter, low-value, cleanup candidate, or unsure.
- Generates one short digest per Gmail account.
- Generates a polished local HTML preview for the digest.
- Generates an optional WhatsApp click-to-chat preview link.
- Suggests 1-2 recurring cleanup senders.
- Stores only local preference memory, not full email bodies.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

2. Copy the example files:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

3. Create a Google OAuth client:

- In Google Cloud Console, create an OAuth client for a desktop app.
- Enable the Gmail API.
- Download the OAuth client JSON.
- Save it as `credentials/google-oauth-client.json`.

4. Edit `config.yaml`:

- Set your first Gmail account under `gmail.accounts`.
- Set `digest.recipient_email` to the email address where you want digests.
- Optional: set `whatsapp.phone_number` to your international phone number for a click-to-chat preview link.

5. Optional AI classification:

- Leave `AI_PROVIDER=disabled` for rules-only classification.
- Set `AI_PROVIDER=openai` and `OPENAI_API_KEY=...` to enable AI classification for uncertain messages.
- Install AI dependencies with `python -m pip install -e '.[ai,dev]'`.

6. Configure digest sending in `.env`:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM`

Use a separate sender credential. The scanned Gmail accounts remain read-only.

## Commands

First 90-day scan for the first configured account:

```bash
gmail-digest --config config.yaml scan --mode first
```

Generate a digest from a scan:

```bash
gmail-digest --config config.yaml digest --scan-file .local/scans/primary.json
```

This writes:

- `.local/digests/primary.txt`
- `.local/digests/primary.html`
- `.local/digests/primary.whatsapp.url` when `whatsapp.phone_number` is configured

Send a digest:

```bash
gmail-digest --config config.yaml send --digest-file .local/digests/primary.txt
```

Run scan + digest for all configured accounts:

```bash
gmail-digest --config config.yaml run --mode daily
```

Run scan + digest + email delivery:

```bash
gmail-digest --config config.yaml run --mode daily --send
```

## Local Files

These files are intentionally ignored by Git:

- `.env`
- `.local/`
- `credentials/`
- Gmail OAuth tokens
- generated scans, classifications, and digests

Generated scan files store metadata, headers, labels, and Gmail snippets only. They do not store full email bodies.

## Tests

```bash
python -m pytest
```
