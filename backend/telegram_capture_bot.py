"""
telegram_capture_bot.py

Text-only Telegram capture surface (interim).
- Mobile-first, chat-based
- Voice capture intentionally NOT implemented yet (must be added later)

Behavior:
- Any text message -> POST {source, text} to backend /v1/raw-events
- Replies only with "Logged ✅" (or a short error)
"""

import json
import os
import sys
import urllib.request
import urllib.error

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters


BACKEND_URL = os.environ.get("PCO_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
RAW_EVENTS_URL = f"{BACKEND_URL}/v1/raw-events"
API_KEY = os.environ.get("PCO_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _post_raw_event(source: str, text: str) -> tuple[bool, str]:
    if not API_KEY:
        return False, "PCO_API_KEY not set"

    payload = {"source": source, "text": text}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        RAW_EVENTS_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            # any 2xx counts as ok
            return True, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return False, f"HTTP {e.code}: {body}".strip()
    except Exception as e:
        return False, str(e)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("PCO capture bot is running. Send me a message to log it.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send a text message and I'll log it. (Voice capture will be added later.)"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    ok, detail = _post_raw_event("telegram", text)
    if ok:
        await update.message.reply_text("Logged ✅")
    else:
        # Keep it short; no coaching, no questions.
        await update.message.reply_text(f"Log failed: {detail[:180]}")


def _die(msg: str) -> None:
    print(f"[telegram_capture_bot] {msg}")
    sys.exit(2)


def main() -> None:
    if not BOT_TOKEN:
        _die("TELEGRAM_BOT_TOKEN is not set")
    if not API_KEY:
        _die("PCO_API_KEY is not set (needed to call backend)")

    print("===========================================================")
    print("[telegram_capture_bot] starting")
    print(f"[telegram_capture_bot] backend: {BACKEND_URL}")
    print("[telegram_capture_bot] mode: text-only (voice later)")
    print("===========================================================")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Long polling
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
