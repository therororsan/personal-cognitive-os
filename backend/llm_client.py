# llm_client.py — Minimal Grok (xAI) client via OpenAI SDK compatibility
import os
import json
from datetime import datetime
from openai import OpenAI, OpenAIError
from typing import List, Dict, Optional

# Config — easy to change provider later
LLM_PROVIDER = "xai"                # can become "openai", "anthropic", "ollama", etc.
BASE_URL = "https://api.x.ai/v1"    # xAI endpoint
MODEL = "grok-4-1-fast-reasoning"   # current fast/reasoning model; change as needed
API_KEY_ENV = "XAI_API_KEY"

client = OpenAI(
    api_key=os.getenv(API_KEY_ENV),
    base_url=BASE_URL,
    timeout=90.0,  # generous for reasoning models
)

def _load_latest_psych_snapshot(user_id: str) -> str:
    """Minimal loader — adapt path if your user_id mapping changes"""
    episodes_dir = os.path.join(os.path.dirname(__file__), "logs", "episodes", user_id)
    if not os.path.exists(episodes_dir):
        return "No recent psychological snapshot available."

    # Find most recent .json (naive sort by name/date)
    files = [f for f in os.listdir(episodes_dir) if f.endswith(".json")]
    if not files:
        return "No episode artifacts found."

    latest_file = max(files)  # lexical sort usually works for YYYY-MM-DD
    path = os.path.join(episodes_dir, latest_file)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        psych = data.get("psychological_status", "Not available")
        recap = data.get("recap", "No recap")
        return f"Latest snapshot ({data.get('date', 'unknown')}):\nStatus: {psych}\nRecap: {recap}"
    except Exception:
        return "Error reading latest snapshot."

def _load_recent_memory_candidates(user_id: str, tail_limit: int = 20, min_conf: float = 0.55) -> List[Dict]:
    """Reuse your existing memory v0 logic style — read-only"""
    memory_dir = os.path.join(os.path.dirname(__file__), "logs", "memory", user_id)
    memory_file = os.path.join(memory_dir, "memory_v0.jsonl")
    if not os.path.exists(memory_file):
        return []

    candidates = []
    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("confidence", 0) >= min_conf:
                        candidates.append(entry)
                except:
                    pass
        # Most recent first, take tail
        return candidates[-tail_limit:]
    except Exception:
        return []

def _format_memory_block(candidates: List[Dict]) -> str:
    if not candidates:
        return ""
    lines = ["\nWeak-signal memory candidates (read-only, confidence-weighted):"]
    for c in candidates[-3:]:  # show last 3 max
        lines.append(f"- {c.get('statement', '—')} (conf: {c.get('confidence','?')}, from: {c.get('source_episode_path','?')})")
    return "\n".join(lines)

def build_advisor_prompt(
    question: str,
    mode: str,
    user_id: str,
    thread_history: List[Dict[str, str]],  # [{"role":"user/assistant", "content": "..."}]
    memory_block: str = ""
) -> List[Dict[str, str]]:
    # Phase 1: Strong long-term memory-aware persona (continuity across weeks/months)
    system = (
        "You are my long-term cognitive advisor — a wise, direct, psychologically informed companion who has known me for months and years. You remember our previous conversations, notice recurring patterns in my behavior, energy, clarity, and decisions, and reference them naturally when relevant. You have deep knowledge of psychology, decision theory, career strategy, and human behavioral patterns. You are non-therapeutic, never diagnose or give clinical treatment advice. Always stay actionable, reflective, and grounded. Speak naturally like a smart, slightly dry-humored friend over coffee. Use second-person language ('you'). Be concise when tactical, deeper when exploring patterns or big decisions. Occasionally ask one sharp clarifying question only when truly needed. If I mention something from past chats, acknowledge it briefly to build continuity."
    )

    context_parts = []

    # Psychological snapshot (highest priority)
    snapshot = _load_latest_psych_snapshot(user_id)
    if snapshot:
        context_parts.append(f"Current psychological snapshot:\n{snapshot}")

    # Memory candidates
    if memory_block:
        context_parts.append(memory_block)

    # Thread history (for follow-ups)
    history_text = ""
    if thread_history:
        history_text = "\nRecent conversation:\n" + "\n".join(
            f"{turn['role'].upper()}: {turn['content'][:300]}" for turn in thread_history[-4:]
        )

    user_content = (
        f"Mode: {mode}\n"
        f"User question: {question}\n\n"
        f"{'\n\n'.join(context_parts)}\n"
        f"{history_text}\n\n"
        "Respond thoughtfully:"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content.strip()}
    ]

    return messages

def generate_advisor_response(
    question: str,
    mode: str,
    user_id: str,
    thread_history: List[Dict[str, str]],
) -> str:
    """Core LLM call — fail-open"""
    try:
        memory_candidates = _load_recent_memory_candidates(user_id)
        memory_block = _format_memory_block(memory_candidates)

        messages = build_advisor_prompt(question, mode, user_id, thread_history, memory_block)

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7 if mode == "DEEP" else 0.4,  # slightly more creative in DEEP
            max_tokens=1200,
        )

        answer = response.choices[0].message.content.strip()
        if not answer:
            return "The reasoning engine returned an empty response. Try rephrasing."
        return answer

    except OpenAIError as e:
        return f"Connection issue with reasoning engine: {str(e)[:120]}. Please try again in a moment."
    except Exception as e:
        return "Internal error while preparing advice. Try again or contact operator."