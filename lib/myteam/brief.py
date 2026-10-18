"""The briefing: one line per member saying what they are doing right now.

Sources, best first:
  1. the member's own note   — `myteam now "planning the CNY party"`
                               (members/<name>/NOW.json; the team-collab skill
                               tells every agent to set it when work starts)
  2. the session's title      — Claude Code names its tmux pane after the
                               conversation ("✳ NSF 26-512 key items"), so this
                               works even for work you typed in directly
  3. their newest open task   — from the board
  4. the last message sent to them over the bus
"""
import json
import re
import socket
import subprocess
import time

from . import board, config, sessions, status

NOTE_FRESH = 6 * 3600          # a self-note older than this loses to the title
_GLYPHS = re.compile(r"^[^\w一-鿿]+")
_BORING = {"", "claude", "codex", "bash", "zsh", "sh", "python3", "node",
           "claude code"}


def set_now(member_name, text):
    d = config.member_dir(member_name)
    (d / "NOW.json").write_text(json.dumps(
        {"ts": round(time.time()), "text": text.strip()}) + "\n")


def _note(member_name):
    p = config.STATE / "members" / member_name / "NOW.json"
    try:
        rec = json.loads(p.read_text())
        return rec.get("text", ""), rec.get("ts", 0)
    except (OSError, ValueError):
        return "", 0


def _title(session):
    try:
        r = subprocess.run(["tmux", "display-message", "-p", "-t", session,
                            "#{pane_title}"], capture_output=True, text=True,
                           timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    t = _GLYPHS.sub("", r.stdout.strip()).strip()
    host = socket.gethostname()
    if t.lower() in _BORING or t in (host, host.split(".")[0]) \
            or t.endswith(".local"):
        return ""
    return t


def _last_msg(session):
    p = config.STATE / "bus" / "{}.log.jsonl".format(session)
    try:
        with open(p, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 4096))
            lines = f.read().decode("utf-8", "replace").splitlines()
        rec = json.loads(lines[-1])
        return rec.get("text", ""), rec.get("ts", 0)
    except (OSError, ValueError, IndexError):
        return "", 0


def ago(ts):
    if not ts:
        return ""
    s = max(0, int(time.time() - ts))
    if s < 90:
        return "now"
    if s < 5400:
        return "{}m".format(s // 60)
    if s < 172800:
        return "{}h".format(s // 3600)
    return "{}d".format(s // 86400)


def collect(cfg, statuses, live=None):
    """[{m, status, doing, src, ts, tasks}] for every member."""
    live = sessions.list_sessions() if live is None else live
    open_tasks = board.listing()
    out = []
    for m in cfg["members"]:
        sess = sessions.sname(m["name"])
        st = statuses.get(m["name"], "off")
        mine = [t for t in open_tasks if t.get("owner") == m["name"]]
        note, nts = _note(m["name"])
        title = _title(sess) if sess in live else ""
        doing, src, ts = "", "", 0
        if st == "blocked" and sess in live:
            why = status.blocked_reason(sessions.tail(sess, 30))
            doing = "⚠ needs you{} — `open {}`".format(
                ": " + why[:70] if why else "", config.display(m).lower())
            src = "blocked"
        elif note and (time.time() - nts < NOTE_FRESH or not title):
            doing, src, ts = note, "note", nts
        elif title:
            doing, src = title, "title"
        elif mine:
            doing, src, ts = "task #{}: {}".format(mine[-1]["id"], mine[-1]["task"]), \
                "task", mine[-1].get("ts", 0)
        else:
            txt, mts = _last_msg(sess)
            if txt:
                queued = st in ("off", "blocked")
                doing, src, ts = ("inbox: " if queued else "last msg: ") + txt, "msg", mts
        out.append({"m": m, "status": st, "doing": " ".join(doing.split()),
                    "src": src, "ts": ts, "tasks": len(mine)})
    return out


def text_report(cfg, statuses):
    """Plain-text briefing for `myteam brief` and the control room's `brief`."""
    rows = collect(cfg, statuses)
    lines = ["═══ {} — briefing {} ═══".format(cfg["group"], time.strftime("%H:%M"))]
    for r in rows:
        m = r["m"]
        extra = []
        if r["tasks"]:
            extra.append("{} open task(s)".format(r["tasks"]))
        if r["ts"]:
            extra.append(ago(r["ts"]))
        lines.append("  {:<10} {:<8} {}{}".format(
            config.display(m), r["status"], r["doing"] or "—",
            "  ({})".format(", ".join(extra)) if extra else ""))
    return "\n".join(lines)
