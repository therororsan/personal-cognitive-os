# PCO TELEGRAM CAPTURE BOT — APPROVAL GATE v1 + ADVISOR MVP A1 (2026-02-05)
import json
import os
import tempfile
import urllib.request
import uuid
import hashlib
import asyncio
from datetime import datetime, timezone
from collections import deque
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from llm_client import generate_advisor_response

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

# Advisor run logs (operator-visible; file-based; no DB/schema changes)
ADVISOR_RUNS_DIR = os.path.join(os.path.dirname(__file__), "logs", "advisor_runs")

# Callback data prefix (kept short for Telegram limits)
CB_PREFIX = "pco"

# Advisor (Telegram-only surface; core intent is surface-agnostic)
ADVISOR_SESSION_KEY = "advisor_session"
ADVISOR_DEFAULT_MODE_KEY = "advisor_default_mode"

# --- Layer 3 (Memory v0) integration (read-only) ---
# Resolution order:
# 1) PCO_MEMORY_USER_ID (explicit, deterministic)
# 2) if exactly 1 directory exists under backend/logs/memory/, use it
# 3) otherwise: no memory injected (fail open)
MEMORY_USER_ID_ENV = "PCO_MEMORY_USER_ID"
MEMORY_TAIL_LIMIT = int(os.environ.get("PCO_MEMORY_TAIL_LIMIT", "20"))
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "logs", "memory")


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


# --- Advisor run logging (operator-visible artifacts; append-only JSONL) ---

def _ensure_advisor_runs_dir() -> None:
    os.makedirs(ADVISOR_RUNS_DIR, exist_ok=True)


def _local_date_str() -> str:
    # Use local timezone for filenames to match operator expectations.
    return datetime.now().astimezone().date().isoformat()


def _sha256_text(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _try_extract_raw_event_id(body: str) -> str | None:
    try:
        obj = json.loads(body)
        if isinstance(obj, dict):
            v = obj.get("id")
            return str(v) if v else None
    except Exception:
        return None
    return None


def _append_advisor_run(record: dict) -> None:
    _ensure_advisor_runs_dir()
    path = os.path.join(ADVISOR_RUNS_DIR, f"{_local_date_str()}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# In-memory aggregation for operator-visible RUN_COMPLETE summary lines.
# Best-effort only: never required for core bot behavior.
_ADVISOR_RUN_STATS: dict[str, dict[str, object]] = {}


def _update_advisor_run_stats(
    *,
    event: str,
    run_id: str,
    mode: str | None,
    answer_len: int,
) -> dict[str, object]:
    e = str(event or "").upper()
    rid = str(run_id)
    st = _ADVISOR_RUN_STATS.get(rid)
    if st is None:
        st = {
            "started_at_utc": _utc_now_iso(),
            "turns": 0,
            "total_answer_chars": 0,
            "final_mode": None,
            "last_event": None,
        }
        _ADVISOR_RUN_STATS[rid] = st

    if e in {"ANSWER", "FOLLOWUP"}:
        st["turns"] = int(st.get("turns", 0)) + 1
        st["total_answer_chars"] = int(st.get("total_answer_chars", 0)) + int(answer_len or 0)
        st["final_mode"] = (str(mode).upper() if mode else st.get("final_mode"))
        st["last_event"] = e
    elif e == "ASK":
        st["last_event"] = e
        if mode:
            st["final_mode"] = str(mode).upper()

    return st


def _emit_run_complete_summary(
    *,
    run_id: str,
    chat_id: int | None,
    telegram_user_id: int | None,
    question: str,
    stats: dict[str, object],
) -> None:
    rec = {
        "ts_utc": _utc_now_iso(),
        "event": "RUN_COMPLETE",
        "run_id": run_id,
        "turn": int(stats.get("turns", 0)),
        "telegram_chat_id": chat_id,
        "telegram_user_id": telegram_user_id,
        "mode": stats.get("final_mode"),
        "question": (question or "").strip(),
        "user_text": None,
        "answer_text": None,
        "answer_len": int(stats.get("total_answer_chars", 0)),
        "answer_sha256": None,
        "raw_event_ok": None,
        "raw_event_id": None,
        "started_at_utc": stats.get("started_at_utc"),
        "ended_at_utc": _utc_now_iso(),
        "last_event": stats.get("last_event"),
        "total_answer_chars": int(stats.get("total_answer_chars", 0)),
        "turns_so_far": int(stats.get("turns", 0)),
    }
    try:
        _append_advisor_run(rec)
    except Exception:
        pass


def _log_advisor_event(
    *,
    event: str,
    run_id: str,
    turn: int,
    chat_id: int | None,
    telegram_user_id: int | None,
    mode: str | None,
    question: str,
    user_text: str | None = None,
    answer_text: str | None = None,
    raw_event_ok: bool | None = None,
    raw_event_body: str | None = None,
) -> None:
    q = (question or "").strip()
    u = (user_text or "").strip() if user_text else None
    a = (answer_text or "").strip() if answer_text else None

    rec = {
        "ts_utc": _utc_now_iso(),
        "event": str(event or "").upper(),
        "run_id": run_id,
        "turn": int(turn),
        "telegram_chat_id": chat_id,
        "telegram_user_id": telegram_user_id,
        "mode": (str(mode).upper() if mode else None),
        "question": q,
        "user_text": u,
        "answer_text": a,
        "answer_len": len(a) if a else 0,
        "answer_sha256": _sha256_text(a) if a else None,
        "raw_event_ok": raw_event_ok,
        "raw_event_id": _try_extract_raw_event_id(raw_event_body or "") if raw_event_body else None,
    }

    # Keep this best-effort: never break bot flow due to logging.
    try:
        _append_advisor_run(rec)
    except Exception:
        pass

    # Also emit a compact RUN_COMPLETE summary after each produced answer.
    if rec.get("event") in {"ANSWER", "FOLLOWUP"}:
        stats = _update_advisor_run_stats(
            event=rec.get("event") or "",
            run_id=run_id,
            mode=rec.get("mode"),
            answer_len=int(rec.get("answer_len") or 0),
        )
        _emit_run_complete_summary(
            run_id=run_id,
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            question=q,
            stats=stats,
        )


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


# --- Memory v0 helpers (read-only) ---

def _resolve_memory_user_dir() -> str | None:
    if not os.path.isdir(MEMORY_DIR):
        return None

    explicit = (os.environ.get(MEMORY_USER_ID_ENV) or "").strip()
    if explicit:
        p = os.path.join(MEMORY_DIR, explicit)
        return p if os.path.isdir(p) else None

    # Heuristic: if only one user dir exists, use it
    try:
        dirs = [
            os.path.join(MEMORY_DIR, d)
            for d in os.listdir(MEMORY_DIR)
            if os.path.isdir(os.path.join(MEMORY_DIR, d))
        ]
    except Exception:
        return None

    if len(dirs) == 1:
        return dirs[0]
    return None


def _load_recent_memory_candidates(limit: int = MEMORY_TAIL_LIMIT) -> list[dict[str, Any]]:
    user_dir = _resolve_memory_user_dir()
    if not user_dir:
        return []

    fpath = os.path.join(user_dir, "memory_v0.jsonl")
    if not os.path.isfile(fpath):
        return []

    dq: deque[dict[str, Any]] = deque(maxlen=max(1, int(limit or 20)))
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        dq.append(obj)
                except Exception:
                    continue
    except Exception:
        return []

    return list(dq)


def _format_memory_block(entries: list[dict[str, Any]]) -> str | None:
    if not entries:
        return None

    lines: list[str] = []
    lines.append("**MEMORY CANDIDATES (weak-signal; confidence-weighted):**")
    for e in entries:
        ctype = str(e.get("candidate_type") or "").strip()
        stmt = str(e.get("statement") or "").strip()
        conf = e.get("confidence")
        sal = e.get("salience")
        src_date = str(e.get("source_episode_date") or "").strip()
        if not stmt:
            continue

        tag = f"[{ctype}]" if ctype else "[memory]"
        meta = []
        if isinstance(conf, (int, float)):
            meta.append(f"conf={conf:.2f}")
        if isinstance(sal, (int, float)):
            meta.append(f"sal={sal:.2f}")
        if src_date:
            meta.append(f"src={src_date}")
        meta_s = ("; " + ", ".join(meta)) if meta else ""
        lines.append(f"- {tag} {stmt}{meta_s}")

    if len(lines) <= 1:
        return None
    return "\n".join(lines)


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


def _build_ask_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⚡ FAST", callback_data=f"{CB_PREFIX}:ask:fast"),
                InlineKeyboardButton("🧠 DEEP", callback_data=f"{CB_PREFIX}:ask:deep"),
            ]
        ]
    )


def _build_ask_followup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⚡ Fast follow-up", callback_data=f"{CB_PREFIX}:ask:ff"),
                InlineKeyboardButton("🧠 Deep follow-up", callback_data=f"{CB_PREFIX}:ask:df"),
            ],
            [InlineKeyboardButton("✅ Done", callback_data=f"{CB_PREFIX}:ask:done")],
        ]
    )


def _format_transcript(text: str, limit: int = 3800) -> str:
    # Telegram message limit is ~4096 chars; keep headroom for safety.
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[:limit].rstrip() + " …"


def _advisor_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    s = context.user_data.get(ADVISOR_SESSION_KEY)
    return bool(s and isinstance(s, dict) and s.get("active"))


def _advisor_get_mode(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    mode = context.user_data.get(ADVISOR_DEFAULT_MODE_KEY)
    if not mode:
        return None
    mode = str(mode).strip().upper()
    return mode if mode in ("FAST", "DEEP") else None


def _advisor_set_mode(context: ContextTypes.DEFAULT_TYPE, mode: str | None) -> None:
    if not mode:
        context.user_data.pop(ADVISOR_DEFAULT_MODE_KEY, None)
        return
    m = str(mode).strip().upper()
    if m in ("FAST", "DEEP"):
        context.user_data[ADVISOR_DEFAULT_MODE_KEY] = m


def _advisor_start_session(context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
    context.user_data[ADVISOR_SESSION_KEY] = {
        "active": True,
        "run_id": uuid.uuid4().hex[:12],
        "turn": 0,
        "question": question,
        "history": [{"role": "user", "content": question, "ts": _utc_now_iso()}],
        "mode": _advisor_get_mode(context) or None,  # selected later if None
        "ask_message_id": None,
        "asked_at_utc": _utc_now_iso(),
    }


def _advisor_end_session(context: ContextTypes.DEFAULT_TYPE) -> None:
    s = context.user_data.get(ADVISOR_SESSION_KEY)
    if isinstance(s, dict):
        s["active"] = False
    context.user_data.pop(ADVISOR_SESSION_KEY, None)




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
        "Cancel edit: tap ❌ Cancel (or /cancel).\n\n"
        "Advisor: /ask <question>\n"
        "Mode: /mode fast | /mode deep | /mode clear"
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Backstop for users who prefer typing.
    context.user_data.pop("edit_pending_id", None)
    await update.message.reply_text("Cancelled.")


async def mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    arg = ""
    if context.args:
        arg = " ".join(context.args).strip()
    else:
        # allow "/mode deep" typed with extra spaces
        arg = (update.message.text or "").replace("/mode", "", 1).strip()

    a = (arg or "").strip().lower()

    if a in ("fast", "f"):
        _advisor_set_mode(context, "FAST")
        await update.message.reply_text("Advisor default mode set: ⚡ FAST")
        return

    if a in ("deep", "d"):
        _advisor_set_mode(context, "DEEP")
        await update.message.reply_text("Advisor default mode set: 🧠 DEEP")
        return

    if a in ("clear", "reset", "off", "none"):
        _advisor_set_mode(context, None)
        await update.message.reply_text("Advisor default mode cleared (will ask each time).")
        return

    await update.message.reply_text("Usage: /mode fast | /mode deep | /mode clear")


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _advisor_active(context):
        _advisor_end_session(context)
        await update.message.reply_text("Advisor session ended. Back to capture.")
    else:
        await update.message.reply_text("No active advisor session.")


# Phase 1: Conversational long-term advisor mode – natural back-and-forth dialogue
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    question = " ".join(context.args).strip()
    print("[DEBUG] ask_cmd started with question:", question)
    if not question:
        await update.message.reply_text("Please provide a question after /ask")
        return

    chat_id = update.message.chat_id
    telegram_user_id = update.message.from_user.id if update.message.from_user else None

    message_id = getattr(update.message, "message_id", None)
    # Dedupe: the same Telegram message can be delivered more than once (or multiple handlers can see it).
    # We treat a given /ask message_id as idempotent.
    existing = context.user_data.get(ADVISOR_SESSION_KEY)
    if isinstance(existing, dict) and existing.get("active") and existing.get("ask_message_id") == message_id:
        return

    _advisor_start_session(context, question)
    session = context.user_data.setdefault(ADVISOR_SESSION_KEY, {})
    if isinstance(session, dict):
        session["ask_message_id"] = message_id
        session["asked_at_utc"] = _utc_now_iso()
    run_id = session.get("run_id") if isinstance(session, dict) else uuid.uuid4().hex[:12]
    turn = int(session.get("turn", 0)) if isinstance(session, dict) else 0

    # Log question as raw event (surface-agnostic; schema remains {source,text})
    ok, body = _post_raw_event("telegram_advisor", f"ASK\nMODE=(pending)\nQ: {question}")
    _log_advisor_event(
        event="ASK",
        run_id=str(run_id),
        turn=turn,
        chat_id=chat_id,
        telegram_user_id=telegram_user_id,
        mode=None,
        question=question,
        raw_event_ok=ok,
        raw_event_body=body,
    )

    mode = session.get(ADVISOR_DEFAULT_MODE_KEY) if isinstance(session, dict) else None
    if not mode:
        mode = "FAST"

    mode = str(mode).upper()
    if mode not in ("FAST", "DEEP"):
        mode = "FAST"
    if isinstance(session, dict):
        session["mode"] = mode

    print("[DEBUG] Selected mode:", mode)

    user_id = os.getenv("PCO_MEMORY_USER_ID") or "094ebda7-4004-422d-8857-7ee773756a6d"
    print("[DEBUG] Calling LLM with user_id:", user_id)
    try:
        answer = await asyncio.to_thread(
            generate_advisor_response,
            question,
            mode,
            user_id=user_id,
            thread_history=_get_advisor_history(context),
        )
    except Exception:
        answer = "Sorry, reasoning engine unavailable right now — try again soon"

    _advisor_append(context, "user", question)
    _advisor_append(context, "assistant", answer)

    ok, body = _post_raw_event("telegram_advisor", f"ANSWER\nMODE={mode}\nQ: {question}\n\n{answer}")
    _log_advisor_event(
        event="ANSWER",
        run_id=str(run_id),
        turn=turn,
        chat_id=chat_id,
        telegram_user_id=telegram_user_id,
        mode=mode,
        question=question,
        answer_text=answer,
        raw_event_ok=ok,
        raw_event_body=body,
    )

    await update.message.reply_text(answer, reply_markup=_build_ask_followup_keyboard())


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

    # Phase 1: Normal text messages = advisor follow-up when session active (critical for conversational flow)
    if _advisor_active(context) and not text.startswith("/"):
        print("[DEBUG] Follow-up text message routed to LLM: " + text)
        session = context.user_data.get(ADVISOR_SESSION_KEY, {})
        mode = (session.get("mode") if isinstance(session, dict) else None) or _advisor_get_mode(context) or "FAST"
        history = _get_advisor_history(context)

        user_id = os.getenv("PCO_MEMORY_USER_ID") or "094ebda7-4004-422d-8857-7ee773756a6d"
        try:
            answer = await asyncio.to_thread(
                generate_advisor_response,
                text,
                mode,
                user_id=user_id,
                thread_history=history,
            )
        except Exception:
            answer = "Sorry, reasoning engine unavailable right now — try again soon"

        _advisor_append(context, "user", text)
        _advisor_append(context, "assistant", answer)

        await update.message.reply_text(answer, reply_markup=_build_ask_followup_keyboard())
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
    # Expect: "pco:<action>:<id>"
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CB_PREFIX:
        return

    action = parts[1]
    pending_id = parts[2]

    # Advisor callbacks (do not touch capture state/files)
    if action == "ask":
        # pending_id here is actually the ask sub-action: fast|deep|ff|df|done
        sub = (pending_id or "").strip().lower()
        if sub in ("fast", "deep"):
            mode = "FAST" if sub == "fast" else "DEEP"
            session = context.user_data.setdefault(ADVISOR_SESSION_KEY, {})
            question = session.pop("pending_question", None) if isinstance(session, dict) else None
            if not question:
                await q.message.reply_text("No pending question")
                return

            user_id = os.getenv("PCO_MEMORY_USER_ID") or "094ebda7-4004-422d-8857-7ee773756a6d"
            try:
                answer = await asyncio.to_thread(
                    generate_advisor_response,
                    question,
                    mode,
                    user_id=user_id,
                    thread_history=[],
                )
            except Exception:
                answer = "Sorry, reasoning engine unavailable right now — try again soon"

            _advisor_append(context, "user", question)
            _advisor_append(context, "assistant", answer)
            if isinstance(session, dict):
                # FIX: make the chosen mode sticky so future /ask use it automatically
                session["mode"] = mode
                context.user_data[ADVISOR_DEFAULT_MODE_KEY] = mode

            ok, body = _post_raw_event("telegram_advisor", f"ANSWER\nMODE={mode}\nQ: {question}\n\n{answer}")
            run_id = session.get("run_id") if isinstance(session, dict) else uuid.uuid4().hex[:12]
            turn = int(session.get("turn", 0)) if isinstance(session, dict) else 0
            _log_advisor_event(
                event="ANSWER",
                run_id=str(run_id),
                turn=turn,
                chat_id=q.message.chat_id if q.message else None,
                telegram_user_id=q.from_user.id if q.from_user else None,
                mode=mode,
                question=str(question or ""),
                answer_text=answer,
                raw_event_ok=ok,
                raw_event_body=body,
            )

            await q.message.reply_text(answer, reply_markup=_build_ask_followup_keyboard())
            return

        if sub in ("ff", "df"):
            mode = "FAST" if sub == "ff" else "DEEP"
            session = context.user_data.get(ADVISOR_SESSION_KEY)
            if isinstance(session, dict):
                session["mode"] = mode
            await q.message.reply_text(f"Follow-ups switched to {'⚡ FAST' if mode=='FAST' else '🧠 DEEP'}")
            return

        if sub == "done":
            if _advisor_active(context):
                _advisor_end_session(context)
                await q.message.reply_text("Advisor session ended. Back to capture.")
            else:
                await q.message.reply_text("No active advisor session.")
            return

        return

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


def _advisor_append(context, role: str, content: str):
    session = context.user_data.setdefault(ADVISOR_SESSION_KEY, {})
    history = session.setdefault("history", [])
    history.append({"role": role, "content": content})
    if len(history) > 8:
        history[:] = history[-8:]


def _get_advisor_history(context):
    session = context.user_data.get(ADVISOR_SESSION_KEY, {})
    return session.get("history", [])


def _get_or_set_mode(session, preferred_mode=None):
    if preferred_mode:
        session[ADVISOR_DEFAULT_MODE_KEY] = preferred_mode
    return session.get(ADVISOR_DEFAULT_MODE_KEY, "FAST")  # fallback


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))

    # Advisor MVP A1 (command-based)
    app.add_handler(CommandHandler("mode", mode_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("done", done_cmd))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
