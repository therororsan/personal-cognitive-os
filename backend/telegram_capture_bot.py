import json
import os
import sys
import tempfile
import urllib.request
import urllib.error

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters


BACKEND_URL = os.environ.get("PCO_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
RAW_EVENTS_URL = f"{BACKEND_URL}/v1/raw-events"
API_KEY = os.environ.get("PCO_API_KEY", "")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Transcription provider selector: deepgram | google
TRANSCRIBE_PROVIDER = os.environ.get("PCO_TRANSCRIBE_PROVIDER", "deepgram").lower()

# Deepgram (unchanged, default)
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen?punctuate=true&smart_format=true&language=en"


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
    elif TRANSCRIBE_PROVIDER == "google":
        return _transcribe_google(audio_path)
    else:
        raise RuntimeError(f"Unknown transcription provider: {TRANSCRIBE_PROVIDER}")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("PCO capture bot is running. Send me a message to log it.")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Send a text or voice message and I'll log it.")


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
        await update.message.reply_text(f"Log failed: {detail[:180]}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.voice:
        return

    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await tg_file.download_to_drive(tmp_path)

        transcript = _transcribe(tmp_path)
        ok, detail = _post_raw_event("telegram_voice", transcript)
        if ok:
            await update.message.reply_text("Logged ✅")
        else:
            await update.message.reply_text(f"Log failed: {detail[:180]}")
    except Exception as e:
        await update.message.reply_text(f"Log failed: {str(e)[:180]}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
