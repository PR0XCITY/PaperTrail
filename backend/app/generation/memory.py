"""
In-memory conversation store with TTL-based expiry.

Each session stores up to 20 turns (user + assistant alternating).
Sessions expire after SESSION_TTL_SECONDS of inactivity (default 2 hours).
This is intentionally simple — no disk persistence needed for the current scale.
"""
import time

SESSION_TTL_SECONDS = 7_200  # 2 hours
MAX_TURNS_PER_SESSION = 20

_sessions: dict[str, dict] = {}


def _cleanup_expired() -> None:
    """Remove sessions that have been idle longer than the TTL."""
    now = time.time()
    expired = [
        sid for sid, data in _sessions.items()
        if now - data["last_active"] > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]


def get_history(session_id: str) -> list[dict]:
    """
    Return the conversation history for a session.

    Returns
    -------
    list of {"role": "user"|"assistant", "content": str}
    Returns [] for unknown or expired sessions.
    """
    _cleanup_expired()
    return list(_sessions.get(session_id, {}).get("history", []))


def add_turn(session_id: str, role: str, content: str) -> None:
    """Append one turn to a session, creating it if necessary."""
    if session_id not in _sessions:
        _sessions[session_id] = {"history": [], "last_active": time.time()}

    _sessions[session_id]["history"].append({"role": role, "content": content})
    _sessions[session_id]["last_active"] = time.time()

    # Cap at MAX_TURNS_PER_SESSION to prevent unbounded growth
    if len(_sessions[session_id]["history"]) > MAX_TURNS_PER_SESSION:
        _sessions[session_id]["history"] = _sessions[session_id]["history"][-MAX_TURNS_PER_SESSION:]


def clear_session(session_id: str) -> None:
    """Explicitly delete a session (e.g., when user switches documents)."""
    _sessions.pop(session_id, None)
