"""The task board (~/.myteam/tasks.jsonl) and the standup report."""
import json
import time

from . import bus, config, sessions, status


def _path():
    config.STATE.mkdir(parents=True, exist_ok=True)
    return config.STATE / "tasks.jsonl"


def _all():
    p = _path()
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _write(tasks):
    _path().write_text("".join(json.dumps(t) + "\n" for t in tasks))


def assign(owner, text, by="owner", notify=True):
    tasks = _all()
    tid = max([t["id"] for t in tasks], default=0) + 1
    tasks.append({"id": tid, "ts": round(time.time(), 2), "task": text,
                  "owner": owner, "by": by, "status": "open"})
    _write(tasks)
    note = ""
    if notify:
        outcome = bus.deliver(
            sessions.sname(owner),
            "New task #{} from {}: {}  (when finished: run `myteam done {}` "
            "and put outputs in the shared deliverables folder)".format(tid, by, text, tid),
            sender=by, kind="task")
        note = " ({})".format(outcome)
    return tid, note


def set_status(tid, new_status, note=None):
    tasks = _all()
    for t in tasks:
        if t["id"] == int(tid):
            t["status"] = new_status
            if note:
                t["note"] = note
            _write(tasks)
            return t
    return None


def reassign_owner(old, new):
    """Move a renamed member's tasks to the new key."""
    tasks = _all()
    for t in tasks:
        if t["owner"] == old:
            t["owner"] = new
    _write(tasks)


def unassign_member(name):
    """A retired member's open tasks go back to the pool."""
    tasks = _all()
    n = 0
    for t in tasks:
        if t["owner"] == name and t["status"] != "done":
            t["owner"] = "unassigned"
            n += 1
    _write(tasks)
    return n


def listing(owner=None, all_tasks=False):
    tasks = _all()
    if owner:
        tasks = [t for t in tasks if t["owner"] == owner]
    if not all_tasks:
        tasks = [t for t in tasks if t["status"] != "done"]
    return tasks


def standup(cfg):
    lines = ["═══ {} — standup ═══".format(cfg["group"]), ""]
    live = sessions.list_sessions()
    lines.append("MEMBERS")
    for m in cfg["members"]:
        name = sessions.sname(m["name"])
        if name in live:
            st = status.classify(sessions.tail(name))
            glyph = status.GLYPH[st]
        else:
            st, glyph = "not running", " "
        open_tasks = [t for t in _all()
                      if t["owner"] == m["name"] and t["status"] != "done"]
        queued = len(bus.pending(name))
        extra = []
        if open_tasks:
            extra.append("{} open task(s)".format(len(open_tasks)))
        if queued:
            extra.append("{} queued msg(s)".format(queued))
        if st == "blocked":
            extra.append("NEEDS A HUMAN — `myteam attach {}`".format(m["name"]))
        lines.append("  {} {:<14} {:<18} {}  {}".format(
            glyph, m["name"], m["role"], st, "; ".join(extra)))
    lines.append("")
    lines.append("OPEN TASKS")
    open_all = listing()
    if not open_all:
        lines.append("  (none — assign with `myteam assign <member> \"task\"`)")
    for t in open_all:
        lines.append("  #{:<3} [{:<10}] {:<8} {}".format(
            t["id"], t["owner"][:10], t["status"], t["task"][:70]))
    lines.append("")
    deliv = config.STATE / "deliverables"
    if deliv.exists():
        fresh = sorted(deliv.rglob("*"), key=lambda p: p.stat().st_mtime,
                       reverse=True)
        fresh = [p for p in fresh if p.is_file() and not any(
                 part.startswith(".") for part in p.relative_to(deliv).parts)][:5]
        if fresh:
            lines.append("RECENT DELIVERABLES")
            for p in fresh:
                lines.append("  {}".format(p.relative_to(deliv)))
    return "\n".join(lines)
