"""Member-to-member message bus with polite delivery.

Lessons adopted from herdr: never inject into a blocked member (it is waiting
on a human); a message for a busy/blocked member is QUEUED and the daemon (or
the next `myteam deliver` call) hands it over when the member goes idle.
Everything is logged to ~/.myteam/bus/.
"""
import json
import os
import time

from . import config, sessions, status


def _file(kind, name):
    d = config.STATE / "bus"
    d.mkdir(parents=True, exist_ok=True)
    return d / "{}.{}.jsonl".format(name, kind)


def log(to, sender, text, kind="msg"):
    rec = {"ts": round(time.time(), 2), "kind": kind, "from": sender, "to": to,
           "text": text}
    with open(_file("log", to), "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def sender_name():
    return os.environ.get("MYTEAM_SESSION") or os.environ.get("MYTEAM_MEMBER", "owner")


def current_status(name):
    if name not in sessions.list_sessions():
        return "gone"
    return status.classify(sessions.tail(name))


def _inject(to, rec):
    """Returns False when the session vanished mid-delivery."""
    return sessions.send_text(to, "[myteam {} from {}] {}".format(
        rec["kind"], rec["from"], rec["text"]))


def deliver(to, text, sender=None, kind="msg", force=False):
    """Deliver now if the member is idle; otherwise queue (unless force)."""
    sender = sender or sender_name()
    rec = log(to, sender, text, kind)
    st = current_status(to)
    if st == "gone":
        _queue(to, rec)
        return "queued (member not running — delivered at next start)"
    if force or st == "idle":
        if _inject(to, rec):
            return "delivered"
        _queue(to, rec)
        return "queued (session vanished mid-delivery — redelivered at next start)"
    _queue(to, rec)
    return "queued (member is {} — daemon/deliver will hand it over when idle)".format(st)


def _queue(to, rec):
    with open(_file("queue", to), "a") as f:
        f.write(json.dumps(rec) + "\n")


def pending(to):
    p = _file("queue", to)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def flush(to):
    """Deliver queued messages if the member is idle. Returns count delivered."""
    msgs = pending(to)
    if not msgs or current_status(to) != "idle":
        return 0
    delivered = 0
    for i, rec in enumerate(msgs):
        if not _inject(to, rec):
            # session died mid-flush: keep the undelivered remainder queued
            remainder = msgs[i:]
            _file("queue", to).write_text(
                "".join(json.dumps(r) + "\n" for r in remainder))
            return delivered
        delivered += 1
        time.sleep(0.5)
    _file("queue", to).unlink(missing_ok=True)
    return delivered


def wait_idle(name, timeout=900, settle=3, poll=2.0):
    deadline = time.time() + timeout
    streak = 0
    while time.time() < deadline:
        st = current_status(name)
        if st in ("blocked", "gone"):
            return st
        streak = streak + 1 if st == "idle" else 0
        if streak >= settle:
            return "idle"
        time.sleep(poll)
    return "timeout"


def ask(to, text, sender=None, timeout=900):
    sender = sender or sender_name()
    st = wait_idle(to, timeout=120)  # be polite: wait for a free moment first
    if st != "idle":
        return None, "target is {} — not asked".format(st)
    rec = log(to, sender, text + "  (Question from teammate {} — answer directly "
              "and concisely at the END of your reply.)".format(sender), "ask")
    _inject(to, rec)
    time.sleep(6)
    outcome = wait_idle(to, timeout=timeout)
    if outcome == "idle":
        reply = "\n".join(sessions.reply_of(to, keep=200)) or "\n".join(sessions.tail(to, 60))
        log(sender, to, reply, kind="reply")
        return reply, "idle"
    return None, outcome
