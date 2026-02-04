# PCO TELEGRAM CAPTURE BOT — APPROVAL GATE v1 (2026-02-04)
import json
import os
import tempfile
import urllib.request
import uuid
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BACKEND_URL = os.environ.get("PCO_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
RAW_EVENTS_URL = f"{BACKEND_URL}/v1/raw-events"
API_KEY = os.environ.get("PCO_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Transcription provider selector: deepgram | google
TRANSCRIBE_PROVIDER = os.environ.get("PCO_TRANSCRIBE_PROVIDER", "deepgram").lower()

# Deepgram (unchanged, default)
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen?punctuate=true&smart_format=true&language=en"

# Pending transcript storage (file-based; no DB/schema changes)
PENDING_DIR = os.path.join(os.path.dirname(__file__), "logs", "pending_transcripts")

# Callback data prefix (kept short for Telegram limits)
CB_PREFIX = "pco"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_pending_dir() -> None:
    os.makedirs(PENDING_DIR, exist_ok=True)


def _pending_path(chat_id: int, pending_id: str) -> str:
    safe = f"{chat_id}_{pending_id}".replace(os.sep, "_")
    return os.path.join(PENDING_DIR, f"{safe}.json")


def _write_pending(chat_id: int, pending_id: str, payload: dict) -> None:
    _ensure_pending_dir()
    path = _pending_path(chat_id, pending_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _read_pending(chat_id: int, pending_id: str):
    path = _pending_path(chat_id, pending_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _mark_pending(chat_id: int, pending_id: str, status: str) -> None:
    item = _read_pending(chat_id, pending_id)
    if not item:
        return
    item["status"] = status
    item["status_updated_at"] = _utc_now_iso()
    _write_pending(chat_id, pending_id, item)


def _delete_pending(chat_id: int, pending_id: str) -> None:
    path = _pending_path(chat_id, pending_id)
    try:
        os.remove(path)
    except Exception:
        pass


def _post_raw_event(source: str, text: str) -> tuple[bool, str]:
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
            return True, body
    except Exception as e:
        return False, str(e)


def _transcribe_deepgram(audio_path: str) -> str:
    if not DEEPGRAM_API_KEY:
        raise RuntimeError("DEEPGRAM_API_KEY not set")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    req = urllib.request.Request(
        DEEPGRAM_URL,
        data=audio_bytes,
        method="POST",
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "audio/ogg",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))

    try:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except Exception:
        raise RuntimeError("Deepgram response missing transcript")


def _transcribe_google(audio_path: str) -> str:
    # Requires:
    #   pip install google-cloud-speech
    #   set GOOGLE_APPLICATION_CREDENTIALS=path\to\service_account.json
    try:
        from google.cloud import speech
    except Exception:
        raise RuntimeError("google-cloud-speech not installed")

    client = speech.SpeechClient()

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )

    response = client.recognize(config=config, audio=audio)

    if not response.results:
        raise RuntimeError("Google returned no transcript")

    return response.results[0].alternatives[0].transcript.strip()


def _transcribe(audio_path: str) -> str:
    if TRANSCRIBE_PROVIDER == "deepgram":
        return _transcribe_deepgram(audio_path)
    if TRANSCRIBE_PROVIDER == "google":
        return _transcribe_google(audio_path)
    raise RuntimeError(f"Unknown transcription provider: {TRANSCRIBE_PROVIDER}")


def _build_review_keyboard(pending_id: str) -> InlineKeyboardMarkup:
    # Keep callback_data short: "pco:<action>:<id>"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"{CB_PREFIX}:approve:{pending_id}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"{CB_PREFIX}:edit:{pending_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"{CB_PREFIX}:reject:{pending_id}"),
            ]
        ]
    )


def _build_cancel_keyboard(pending_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel", callback_data=f"{CB_PREFIX}:cancel:{pending_id}")]]
    )


def _format_transcript(text: str, limit: int = 3800) -> str:
    # Telegram message limit is ~4096 chars; keep headroom for safety.
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + " …"


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "PCO capture bot is running.\n\n"
        "Send text or voice.\n"
        "I will show you the transcript and ask you to Approve / Edit / Reject before logging."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Text: send a message → I'll show it for Approve/Edit/Reject.\n"
        "Voice: send a voice message → I'll transcribe and show it for Approve/Edit/Reject.\n"
        "Edit: tap ✏️ Edit → I'll send the transcript as a clean copyable message.\n"
        "Cancel edit: tap ❌ Cancel (or /cancel)."
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Backstop for users who prefer typing.
    context.user_data.pop("edit_pending_id", None)
    await update.message.reply_text("Cancelled.")


async def _send_review(message, transcript: str, pending_id: str) -> None:
    # transcript-only message body + review buttons
    text = _format_transcript(transcript)
    await message.reply_text(text, reply_markup=_build_review_keyboard(pending_id))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    # If user is in "edit transcript" mode, treat this message as the corrected transcript.
    pending_id = context.user_data.get("edit_pending_id")
    if pending_id:
        chat_id = update.message.chat_id
        item = _read_pending(chat_id, pending_id)
        if not item:
            context.user_data.pop("edit_pending_id", None)
            await update.message.reply_text("That pending transcript no longer exists.")
            return

        item["transcript"] = text
        item["edited_at"] = _utc_now_iso()
        item["status"] = "pending"
        _write_pending(chat_id, pending_id, item)

        context.user_data.pop("edit_pending_id", None)

        await update.message.reply_text("Updated.")
        await _send_review(update.message, text, pending_id)
        return

    # Normal text: use the same approval gate as voice.
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id if update.message.from_user else None
    pending_id = uuid.uuid4().hex[:12]

    item = {
        "pending_id": pending_id,
        "chat_id": chat_id,
        "telegram_user_id": user_id,
        "source": "telegram",
        "transcript": text,
        "status": "pending",
        "created_at": _utc_now_iso(),
        "provider": "typed",
    }
    _write_pending(chat_id, pending_id, item)

    await _send_review(update.message, text, pending_id)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    tmp_path = None
    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await tg_file.download_to_drive(tmp_path)

        transcript = _transcribe(tmp_path).strip()
        if not transcript:
            await update.message.reply_text("Transcription produced empty text. Please try again.")
            return

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id if update.message.from_user else None
        pending_id = uuid.uuid4().hex[:12]

        item = {
            "pending_id": pending_id,
            "chat_id": chat_id,
            "telegram_user_id": user_id,
            "source": "telegram_voice",
            "transcript": transcript,
            "status": "pending",
            "created_at": _utc_now_iso(),
            "provider": TRANSCRIBE_PROVIDER,
        }
        _write_pending(chat_id, pending_id, item)

        await _send_review(update.message, transcript, pending_id)

    except Exception as e:
        await update.message.reply_text(f"Voice processing failed: {str(e)[:180]}")
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return

    q = update.callback_query
    await q.answer()

    data = (q.data or "").strip()
    # Expect: "pco:<action>:<pending_id>"
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CB_PREFIX:
        return

    action = parts[1]
    pending_id = parts[2]

    chat_id = q.message.chat_id if q.message else None
    if chat_id is None:
        return

    item = _read_pending(chat_id, pending_id)
    if not item:
        try:
            await q.edit_message_text("This pending transcript no longer exists.")
        except Exception:
            pass
        return

    if action == "approve":
        transcript = (item.get("transcript") or "").strip()
        if not transcript:
            await q.edit_message_text("Transcript is empty; cannot approve.")
            return

        ok, detail = _post_raw_event(item.get("source", "telegram"), transcript)
        if ok:
            _mark_pending(chat_id, pending_id, "approved")
            _delete_pending(chat_id, pending_id)
            await q.edit_message_text("Logged ✅")
        else:
            await q.edit_message_text(f"Log failed: {detail[:180]}")

    elif action == "reject":
        _mark_pending(chat_id, pending_id, "rejected")
        _delete_pending(chat_id, pending_id)
        await q.edit_message_text("Discarded ❌")

    elif action == "edit":
        context.user_data["edit_pending_id"] = pending_id
        transcript = _format_transcript(item.get("transcript", ""))
        # Spec: edit-mode message body should be transcript-only; cancel via button.
        await q.message.reply_text(transcript, reply_markup=_build_cancel_keyboard(pending_id))

    elif action == "cancel":
        if context.user_data.get("edit_pending_id") == pending_id:
            context.user_data.pop("edit_pending_id", None)
        try:
            await q.edit_message_text("Cancelled.")
        except Exception:
            pass
        transcript = (item.get("transcript") or "").strip()
        if transcript and q.message:
            await q.message.reply_text(_format_transcript(transcript), reply_markup=_build_review_keyboard(pending_id))

    else:
        return


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
