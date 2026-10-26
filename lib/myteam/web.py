"""myteam-web — the control room in your browser.

Standard library only (http.server + a background poller). Binds to
127.0.0.1 and protects every request with a per-run token, so nothing else
on the network — and no other website open in your browser — can drive your
team. Running `myteam-web` again just reopens the browser on the live server.
"""
import argparse
import re
import json
import os
import secrets
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import board, brief, bus, config, packs, profile, roles, sessions, skills, status

UI = Path(__file__).with_name("webui")
POLL = 2.0
RUNFILE = config.STATE / "web.json"
TEXT_EXT = {".md", ".txt", ".csv", ".json", ".py", ".log", ".yaml", ".yml",
            ".html", ".tsv", ".tex", ".jsonl", ".sh"}


# ---------------------------------------------------------------- the hub
class Hub:
    """Everything the page shows, kept current by one background thread."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()
        self.feed = []          # {id, ts, kind, text, who}
        self._next = 1
        self.statuses = {}
        self.briefs = []
        self.awaiting = {}
        self._offsets = {}
        self._last_brief = 0
        d = config.STATE / "bus"
        if d.exists():
            for f in d.glob("*.log.jsonl"):
                self._offsets[f] = f.stat().st_size
        from . import team
        mg = team.manager(cfg)
        if mg:
            self.add("sys", "Welcome to the {} control room. Just type — it goes to your "
                     "manager, {}. `inbox` = what needs you · `help` = all commands.".format(
                         cfg["group"], config.display(mg)))
        else:
            ex = config.display(cfg["members"][0]) if cfg["members"] else "name"
            self.add("sys", "Welcome to the {} control room. Type a member's name to "
                     "talk ({}: …), @all to broadcast, or `help`.".format(cfg["group"], ex))

    # feed ---------------------------------------------------------------
    def add(self, kind, text, who=None):
        with self.lock:
            self.feed.append({"id": self._next, "ts": time.time(), "kind": kind,
                              "text": text, "who": who})
            self._next += 1
            self.feed = self.feed[-3000:]

    def since(self, last):
        with self.lock:
            return [e for e in self.feed if e["id"] > last]

    # polling ------------------------------------------------------------
    def loop(self):
        while True:
            try:
                self.poll()
            except Exception as e:      # never let the poller die
                self.add("err", "poller: {!r}".format(e))
            time.sleep(POLL)

    def poll(self):
        self.cfg = config.load() or self.cfg      # hires/edits from the CLI show up
        live = sessions.list_sessions()
        sts = {}
        for m in self.cfg["members"]:
            name = sessions.sname(m["name"])
            if name in live:
                sts[m["name"]] = status.classify(sessions.tail(name))
                bus.flush(name)
            else:
                sts[m["name"]] = "off"
        self.statuses = sts
        if time.time() - self._last_brief > 4:
            self._last_brief = time.time()
            self.briefs = brief.collect(self.cfg, sts, live)
        # agent<->agent traffic
        d = config.STATE / "bus"
        if d.exists():
            for f in sorted(d.glob("*.log.jsonl")):
                pos, size = self._offsets.get(f, 0), f.stat().st_size
                if size <= pos:
                    continue
                with open(f) as fh:
                    fh.seek(pos)
                    chunk = fh.read()
                self._offsets[f] = size
                for line in chunk.splitlines():
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    frm = rec.get("from", "")
                    from . import team
                    mg = team.manager(self.cfg)
                    if mg and rec.get("to") == sessions.sname(mg["name"]) and \
                            rec.get("kind") in ("report", "decision"):
                        self.awaiting[rec["to"]] = time.time()   # the manager will summarize
                    if frm.startswith(sessions.PREFIX):
                        self.add("traffic", "{} → {} [{}] {}".format(
                            short(frm), short(rec.get("to", "?")),
                            rec.get("kind", "msg"), rec.get("text", "")))
        # replies to what the owner sent
        for name, sent in list(self.awaiting.items()):
            if time.time() - sent < 6:
                continue
            st = bus.current_status(name)
            if st == "idle":
                del self.awaiting[name]
                body = "\n".join(sessions.reply_of(name, since=sent))
                self.add("reply", body, who=short(name))
            elif st == "gone":
                del self.awaiting[name]
                self.add("err", "{} exited — start it again from the sidebar".format(short(name)))

    # state for the page -------------------------------------------------
    def state(self):
        from . import team
        by = {r["m"]["name"]: r for r in self.briefs}
        members = []
        for m in self.cfg["members"]:
            r = by.get(m["name"], {})
            members.append({
                "name": m["name"], "display": config.display(m), "role": m["role"],
                "role_zh": roles.zh(m["role"]),
                "role_title": m.get("role_title", ""), "agent": m.get("agent", ""),
                "status": self.statuses.get(m["name"], "off"),
                "doing": re.sub(r" — `open [^`]+`$", "", r.get("doing", "")),
                "src": r.get("src", ""),
                "ago": brief.ago(r.get("ts", 0)), "tasks": r.get("tasks", 0),
                "queued": len(bus.pending(sessions.sname(m["name"]))),
                "manager": team.is_manager(self.cfg, m),
            })
        hired = {m["role"] for m in self.cfg["members"]}
        catalog = [{"id": t["id"], "zh": roles.zh(t["id"]), "title": t["title"],
                    "hired": t["id"] in hired}
                   for t in roles.for_pack(packs.of(self.cfg)["id"])
                   if t["id"] not in team.MANAGER_ROLES]
        mg = team.manager(self.cfg)
        return {"group": self.cfg["group"], "catalog": catalog,
                "manager": config.display(mg) if mg else "",
                "lang": self.cfg.get("prefs", {}).get("lang", "en"),
                "members": members, "tasks": board.listing(),
                "tmux": sessions.tmux_ok(), "time": time.strftime("%H:%M:%S")}

    # commands (same language as the terminal control room) ---------------
    def target(self, token):
        m = config.member(self.cfg, token)
        if m:
            return m
        tl = token.lower()
        exact = [x for x in self.cfg["members"]
                 if tl in (x["name"], config.display(x).lower())]
        hits = exact or [x for x in self.cfg["members"]
                         if tl in x["name"] or tl in config.display(x).lower()]
        return hits[0] if len(hits) == 1 else None

    def start(self, m):
        name = sessions.sname(m["name"])
        if name in sessions.list_sessions():
            return False
        from . import team
        self.add("sys", team.wake(self.cfg, m, by="owner"))   # clears first-run trust prompt
        return True

    def send(self, m, text):
        if self.start(m):
            self.add("sys", "(started {} in the background)".format(config.display(m)))
            time.sleep(1)
        name = sessions.sname(m["name"])
        outcome = bus.deliver(name, text, sender="owner")
        self.awaiting[name] = time.time()
        self.add("me", "you → {}: {}".format(config.display(m), text))
        self.add("sys", "   " + outcome)

    def bring_up(self):
        if not sessions.tmux_ok():
            self.add("err", "needs tmux (conda install -c conda-forge tmux)")
            return
        from . import team
        mg = team.manager(self.cfg)
        started = [config.display(m) for m in ([mg] if mg else self.cfg["members"])
                   if self.start(m)]
        me = config.root() / "bin" / "myteam"
        sessions.run_daemon_session('"{}" daemon run'.format(me))
        self.add("sys", "started: {} (daemon running)".format(", ".join(started))
                 if started else "everyone is already running")

    def handle(self, raw):
        raw = raw.strip()
        if not raw:
            return
        cmd = raw.split()[0].lower().strip(",:;!/")
        rest = raw[len(raw.split()[0]):].strip()
        if cmd in ("help", "h"):
            self.add("sys", HELP)
        elif cmd == "up":
            self.bring_up()
        elif cmd == "start" and rest:
            m = self.target(rest.split()[0])
            if not m:
                self.add("err", "no member '{}'".format(rest))
            else:
                self.add("sys", "started {}".format(config.display(m)) if self.start(m)
                         else "{} already running".format(config.display(m)))
        elif cmd in ("brief", "briefing"):
            self.add("sys", brief.text_report(self.cfg, self.statuses))
        elif cmd == "standup":
            self.add("sys", board.standup(self.cfg))
        elif cmd == "roster":
            self.add("sys", "\n".join("{:<10} {:<20} [{}]  {}".format(
                config.display(m), m["role"], m.get("agent", ""), m.get("focus") or "")
                for m in self.cfg["members"]))
        elif cmd == "tasks":
            rows = board.listing()
            self.add("sys", "\n".join("#{:<3} [{:<10}] {:<8} {}".format(
                t["id"], t["owner"][:10], t["status"], t["task"]) for t in rows)
                or "no open tasks")
        elif cmd == "done" and rest:
            t = board.set_status(rest.split()[0], "done")
            self.add("sys", "✓ done: {}".format(t["task"]) if t else "no such task")
        elif cmd == "assign" and rest:
            parts = rest.split(None, 1)
            m = self.target(parts[0]) if parts else None
            if m and len(parts) == 2:
                tid, note = board.assign(m["name"], parts[1].strip('"'), by="owner")
                self.awaiting[sessions.sname(m["name"])] = time.time()
                self.add("me", "task #{} → {}{}".format(tid, config.display(m), note))
            else:
                self.add("err", "usage: assign <member> <task>")
        elif raw.startswith("@"):
            words, mentions, i = raw.split(), [], 0
            while i < len(words) and words[i].startswith("@"):
                mentions.append(words[i][1:].strip(",:;"))
                i += 1
            text = " ".join(words[i:]).strip()
            if not text:
                self.add("err", "say something after the @mentions")
                return
            targets = (self.cfg["members"] if any(t.lower() == "all" for t in mentions)
                       else [self.target(t) for t in mentions])
            seen = set()
            for m in targets:
                if m and m["name"] not in seen:
                    seen.add(m["name"])
                    self.send(m, text)
            bad = [t for t, m in zip(mentions, targets) if m is None]
            if bad and not any(t.lower() == "all" for t in mentions):
                self.add("err", "no member: {}".format(", ".join(bad)))
        elif cmd in ("inbox", "staff"):
            from . import team
            self.add("sys", team.inbox_text(self.cfg) if cmd == "inbox"
                     else team.staff_text(self.cfg))
        elif cmd in ("approve", "decline") and rest:
            from . import team
            parts = rest.split(None, 1)
            self.add("sys", team.decide(self.cfg, parts[0], cmd == "approve",
                                        parts[1] if len(parts) > 1 else ""))
        else:
            from . import team
            mg = team.manager(self.cfg)
            first = raw.split()[0]
            m = self.target(cmd)
            if m and rest and (not mg or m["name"] == mg["name"] or first[-1] in ":,"):
                self.send(m, rest.lstrip(",:; "))
            elif mg:                             # everything else goes to the manager
                self.send(mg, raw)
            else:
                self.add("err", "not understood — try `help`")


HELP = """talk      just type — it goes to your manager
you       inbox · approve <id> · decline <id> [reason] · staff
direct    bookkeeper: <msg> · @writer <msg> · @all <msg>   (talk to a specialist yourself)
board     assign <m> <task> · tasks · done <id>
views     brief · standup · roster
run       up = start everyone · start <m>
member    click a member to watch their terminal and answer their prompts
files     the Files tab shows deliverables/ and handbook/"""


def short(s):
    return s[len(sessions.PREFIX):] if s.startswith(sessions.PREFIX) else s


# ---------------------------------------------------------------- setup
AGENTS = [("claude", "Claude Code"), ("codex", "Codex"), ("custom", "Other agent CLI")]


def setup_info(cfg):
    import shutil
    from . import team
    return {
        "group": cfg["group"], "lang": cfg.get("prefs", {}).get("lang", "en"),
        "pack": packs.of(cfg)["id"],
        "packs": [{"id": p["id"], "en": p["en"], "zh": p["zh"], "blurb": p["blurb"],
                   "boss": p["boss"]} for p in packs.PACKS],
        "role_groups": [{"pack": pid, "en": packs.get(pid)["en"], "zh": packs.get(pid)["zh"],
                         "roles": [{"id": t["id"], "title": t["title"], "zh": roles.zh(t["id"])}
                                   for t in roles.for_pack(pid)]}
                        for pid in [packs.of(cfg)["id"]] + [p["id"] for p in packs.PACKS
                                                            if p["id"] != packs.of(cfg)["id"]]],
        "profile_title": {"en": profile.title(cfg)[1], "zh": profile.title(cfg)[2]},
        "agents": [{"id": a, "label": l, "installed": bool(shutil.which(a)) if a != "custom" else None}
                   for a, l in AGENTS],
        "profile": profile.get(cfg),
        "profile_fields": [{"key": k, "en": en, "zh": zh, "ph": ph, "multi": ml}
                           for k, en, zh, ph, ml in profile.fields(cfg)],
        "members": [{"name": m["name"], "display": config.display(m), "role": m["role"],
                     "role_zh": roles.zh(m["role"]), "role_title": m.get("role_title", ""), "instructions": m.get("instructions", ""),
                     "focus": m.get("focus", ""), "agent": m.get("agent", ""), "cmd": m.get("cmd", ""),
                     "workdir": str(config.member_dir(m["name"])),
                     "folders": config.member_folders(m),
                     "manager": team.is_manager(cfg, m)}
                    for m in cfg["members"]],
        "state": str(config.STATE),
    }


def _apply_card(m, b, cfg=None):
    rid = (b.get("role") or "").strip()
    pid, _, rid = rid.rpartition(":")          # "teaching:reviewer" picks that preset's card
    tpl = roles.by_id(rid, pid or packs.of(cfg)["id"])
    if tpl:
        m["role"], m["role_title"] = tpl["id"], tpl["title"]
        m.pop("instructions", None)
    else:                                   # custom role
        import re as _re
        m["role"] = _re.sub(r"[^a-z0-9-]+", "-", (b.get("custom_id") or rid or "custom").lower()).strip("-") or "custom"
        m["role_title"] = (b.get("role_title") or m["role"]).strip()
        m["instructions"] = (b.get("instructions") or "").strip()
    m["focus"] = (b.get("focus") or "").strip()
    agent = b.get("agent") or "claude"
    cmd = (b.get("cmd") or "").strip() if agent == "custom" else agent
    if not cmd:
        raise ValueError("an agent command is required")
    m["agent"], m["cmd"] = (agent if agent != "custom" else "custom"), cmd
    folders, bad = config.parse_folders(b.get("folders") or "")
    if bad:
        raise ValueError("can't use: " + "; ".join(bad))
    if folders:
        m["folders"] = folders
    else:
        m.pop("folders", None)


def setup_action(hub, action, b):
    """Returns (ok, message). Every change is saved and skills re-rendered."""
    from .cli import _rename_member, cmd_retire
    cfg = config.load() or hub.cfg
    if action == "team":
        g = (b.get("group") or "").strip()
        if not g:
            return False, "team name can't be empty"
        cfg["group"] = g
        msg = "team renamed to {}".format(g)
    elif action == "hire":
        import re as _re
        from . import team
        disp = (b.get("display") or "").strip()
        rid = (b.get("role") or "").rpartition(":")[2] or b.get("custom_id") or "specialist"
        key = (_re.sub(r"[^a-z0-9-]+", "-", disp.lower()).strip("-") if disp
               else team.specialist_id(cfg, _re.sub(r"[^a-z0-9-]+", "-", rid.lower()).strip("-")
                                       or "specialist", b.get("focus") or ""))
        if not key:                         # e.g. a Chinese name: internal key member-N,
            n = 1                           # the name you see and type stays as written
            while config.member(cfg, "member-{}".format(n)):
                n += 1
            key = "member-{}".format(n)
        if config.member(cfg, key) or any(config.display(x) == disp for x in cfg["members"]):
            return False, "'{}' already exists".format(disp)
        m = {"name": key, "display": disp} if disp else {"name": key}
        try:
            _apply_card(m, b, cfg)
        except ValueError as e:
            return False, str(e)
        cfg["members"].append(m)
        msg = "added {} ({})".format(config.display(m), m["role"])
    elif action == "manager":
        from . import team
        m = config.member(cfg, b.get("name") or "")
        if not m:
            return False, "no such member"
        team.set_manager(cfg, m)
        msg = "{} is now the manager".format(config.display(m))
    elif action == "edit":
        m = config.member(cfg, b.get("name") or "")
        if not m:
            return False, "no such member"
        disp = (b.get("display") or "").strip()
        if disp and disp != config.display(m):
            from . import team
            if team.is_manager(cfg, m):
                _rename_member(cfg, m, disp)
            else:
                m["display"] = disp          # specialists keep their role id; nickname only
        try:
            _apply_card(m, b, cfg)
        except ValueError as e:
            return False, str(e)
        msg = "saved {} — takes effect next time they start".format(config.display(m))
    elif action == "retire":
        m = config.member(cfg, b.get("name") or "")
        if not m:
            return False, "no such member"
        config.save(cfg)
        cmd_retire(cfg, m["name"])           # archives to alumni/, never deletes
        msg = "{} retired — workspace kept in alumni/".format(config.display(m))
    elif action == "profile":
        data = b.get("profile") or {}
        keys = {k for k, *_ in profile.fields(cfg)}
        cfg["profile"] = {k: str(v)[:4000] for k, v in data.items() if k in keys and str(v).strip()}
        msg = "company profile saved — every member's skills updated"
    elif action == "pack":
        pid = b.get("pack")
        if pid not in [p["id"] for p in packs.PACKS]:
            return False, "unknown preset"
        cfg["pack"] = pid
        msg = "preset is now {} — existing members keep their roles".format(packs.get(pid)["en"])
    elif action == "sync":
        msg = "re-rendered shared skills for everyone"
    else:
        return False, "unknown action"
    config.save(cfg)
    skills.sync(cfg)
    hub.cfg = cfg
    hub.add("sys", "setup: " + msg)
    return True, msg


# ---------------------------------------------------------------- files
ROOTS = ("deliverables", "handbook")


def list_files():
    out = []
    for r in ROOTS:
        base = config.STATE / r
        if not base.exists():
            continue
        for p in base.rglob("*"):
            rel = p.relative_to(config.STATE)
            if p.is_file() and not any(x.startswith(".") for x in rel.parts):
                st = p.stat()
                out.append({"path": str(rel), "size": st.st_size, "mtime": st.st_mtime})
    out.sort(key=lambda f: -f["mtime"])
    return out


def safe_path(rel):
    p = (config.STATE / rel).resolve()
    for r in ROOTS:
        base = (config.STATE / r).resolve()
        if p == base or base in p.parents:
            return p if p.is_file() else None
    return None


# ---------------------------------------------------------------- tmux keys
KEYS = {"Enter": "Enter", "Escape": "Escape", "Up": "Up", "Down": "Down",
        "Left": "Left", "Right": "Right", "Tab": "Tab", "BTab": "BTab",
        "Backspace": "BSpace", "Delete": "DC", "Home": "Home", "End": "End",
        "PageUp": "PPage", "PageDown": "NPage", "Space": "Space",
        "C-c": "C-c", "C-d": "C-d", "C-l": "C-l", "C-r": "C-r", "C-o": "C-o"}

_CURSOR = ("❯", "›", "➜", "▶")


def find_menu(lines):
    """Detect an arrow-key menu at the bottom of a terminal (Claude Code's
    trust / permission dialogs, Codex approvals ...). Returns
    {"options": [labels], "selected": i} or None."""
    tail = [re.sub(r"\s*[│┃|]\s*$", "", re.sub(r"^(\s*)[│┃|]", r"\1 ", l))
            for l in lines[-25:]]
    cur = None
    for i in range(len(tail) - 1, -1, -1):
        st = tail[i].strip()
        if st[:1] in _CURSOR and len(st) > 2:
            cur = i
            break
    if cur is None:
        return None

    def is_opt(l):
        st = l.strip()
        return (bool(st) and l[:1] == " " and len(st) < 90 and "·" not in st
                and not st.endswith((":", "?")))
    lo = cur
    while lo - 1 >= 0 and is_opt(tail[lo - 1]):
        lo -= 1
    hi = cur
    while hi + 1 < len(tail) and is_opt(tail[hi + 1]):
        hi += 1
    block = tail[lo:hi + 1]
    if len(block) < 2:
        return None
    labels = []
    for l in block:
        st = l.strip()
        if st[:1] in _CURSOR:
            st = st[1:].strip()
        st = re.sub(r"^\d+[.)]\s*", "", st)
        labels.append(st)
    return {"options": labels, "selected": cur - lo}


def choose(session, index):
    """Move the menu cursor to option `index` and press Enter."""
    menu = find_menu(sessions.tail(session, 60))
    if not menu or not 0 <= index < len(menu["options"]):
        return False
    delta = index - menu["selected"]
    for _ in range(abs(delta)):
        subprocess.run(["tmux", "send-keys", "-t", session, "Down" if delta > 0 else "Up"],
                       capture_output=True)
        time.sleep(0.12)
    time.sleep(0.2)
    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], capture_output=True)
    return True


def send_keys(session, text="", key=None):
    if text:
        subprocess.run(["tmux", "send-keys", "-t", session, "-l", text],
                       capture_output=True)
        time.sleep(0.15)
    if key in KEYS:
        subprocess.run(["tmux", "send-keys", "-t", session, KEYS[key]],
                       capture_output=True)


# ---------------------------------------------------------------- http
def make_handler(hub, token):
    class H(BaseHTTPRequestHandler):
        server_version = "myteam-web"

        def log_message(self, *a):
            pass

        # -- helpers
        def _authed(self):
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                return False             # blocks DNS-rebinding tricks
            if self.headers.get("X-Token") == token:
                return True
            for part in (self.headers.get("Cookie") or "").split(";"):
                k, _, v = part.strip().partition("=")
                if k == "mt" and secrets.compare_digest(v, token):
                    return True
            return False

        def _send(self, code, body, ctype="application/json", extra=None):
            data = body if isinstance(body, bytes) else (
                json.dumps(body) if ctype == "application/json" else body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + ("; charset=utf-8"
                             if ctype.startswith(("text", "application/json")) else ""))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 1_000_000:
                return {}
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def _member(self, name):
            m = hub.target(name or "")
            return m, (sessions.sname(m["name"]) if m else None)

        # -- GET
        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            if u.path == "/api/ping":
                return self._send(200, {"ok": True, "app": "myteam-web"})
            if u.path in ("/", "/index.html"):
                if q.get("t", [""])[0] == token:      # first visit: trade URL token for a cookie
                    return self._send(302, b"", "text/plain", {
                        "Location": "/",
                        "Set-Cookie": "mt={}; HttpOnly; SameSite=Strict; Path=/".format(token)})
                if not self._authed():
                    return self._send(403, "Open the link printed by `myteam-web` "
                                      "(it carries this session's key).", "text/plain")
                return self._send(200, (UI / "index.html").read_bytes(), "text/html")
            if not self._authed():
                return self._send(403, {"error": "forbidden"})
            if u.path == "/api/state":
                return self._send(200, hub.state())
            if u.path == "/api/feed":
                last = int(q.get("since", ["0"])[0] or 0)
                return self._send(200, {"items": hub.since(last)})
            if u.path == "/api/peek":
                m, sess = self._member(q.get("m", [""])[0])
                if not m:
                    return self._send(404, {"error": "no such member"})
                running = sess in sessions.list_sessions()
                lines = sessions.tail(sess, 200) if running else []
                return self._send(200, {
                    "menu": find_menu(lines) if running else None,
                    "member": config.display(m), "running": running,
                    "status": hub.statuses.get(m["name"], "off"),
                    "lines": lines})
            if u.path == "/api/setup":
                return self._send(200, setup_info(config.load() or hub.cfg))
            if u.path == "/api/files":
                return self._send(200, {"files": list_files(), "root": str(config.STATE)})
            if u.path == "/api/file":
                p = safe_path(q.get("p", [""])[0])
                if not p:
                    return self._send(404, {"error": "not found"})
                if p.suffix.lower() in TEXT_EXT and p.stat().st_size < 2_000_000:
                    return self._send(200, p.read_text(errors="replace"), "text/plain")
                return self._send(200, p.read_bytes(), "application/octet-stream", {
                    "Content-Disposition": 'attachment; filename="{}"'.format(p.name)})
            return self._send(404, {"error": "not found"})

        # -- POST
        def do_POST(self):
            if not self._authed():
                return self._send(403, {"error": "forbidden"})
            u = urllib.parse.urlparse(self.path)
            b = self._body()
            if u.path == "/api/input":
                threading.Thread(target=hub.handle, args=(str(b.get("text", ""))[:20000],),
                                 daemon=True).start()
                return self._send(200, {"ok": True})
            if u.path == "/api/start":
                m, _ = self._member(b.get("m"))
                if not m:
                    return self._send(404, {"error": "no such member"})
                if b.get("all"):
                    hub.bring_up()
                else:
                    hub.add("sys", "started {}".format(config.display(m)) if hub.start(m)
                            else "{} already running".format(config.display(m)))
                return self._send(200, {"ok": True})
            if u.path == "/api/up":
                threading.Thread(target=hub.bring_up, daemon=True).start()
                return self._send(200, {"ok": True})
            if u.path == "/api/stop":
                m, sess = self._member(b.get("m"))
                if m and sess in sessions.list_sessions():
                    sessions.kill(sess)
                    hub.add("sys", "stopped {}".format(config.display(m)))
                return self._send(200, {"ok": True})
            if u.path == "/api/keys":
                # the OWNER typing into a member's terminal (e.g. answering a
                # trust prompt) — this is the human, not an agent
                m, sess = self._member(b.get("m"))
                if not m or sess not in sessions.list_sessions():
                    return self._send(404, {"error": "member not running"})
                send_keys(sess, str(b.get("text", ""))[:20000], b.get("key"))
                return self._send(200, {"ok": True})
            if u.path == "/api/choose":
                m, sess = self._member(b.get("m"))
                if not m or sess not in sessions.list_sessions():
                    return self._send(404, {"error": "member not running"})
                ok = choose(sess, int(b.get("index", -1)))
                return self._send(200 if ok else 409, {"ok": ok})
            if u.path.startswith("/api/setup/"):
                ok, msg = setup_action(hub, u.path.rsplit("/", 1)[1], b)
                return self._send(200 if ok else 400, {"ok": ok, "message": msg})
            if u.path == "/api/lang":
                cfg = config.load() or hub.cfg
                cfg.setdefault("prefs", {})["lang"] = "zh" if b.get("lang") == "zh" else "en"
                config.save(cfg)
                hub.cfg = cfg
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})

    return H


# ---------------------------------------------------------------- launcher
def _running():
    try:
        info = json.loads(RUNFILE.read_text())
        with urllib.request.urlopen("http://127.0.0.1:{}/api/ping".format(info["port"]),
                                    timeout=1) as r:
            if json.loads(r.read()).get("app") == "myteam-web":
                return info
    except Exception:
        pass
    return None


def _free_port(preferred):
    for port in [preferred] + list(range(preferred + 1, preferred + 40)) + [0]:
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()
    raise SystemExit("no free port")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="myteam-web",
                                 description="MyTeam control room in your browser")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    ap.add_argument("cmd", nargs="?", choices=["stop", "url"],
                    help="stop: shut down a running server · url: print its link")
    a = ap.parse_args(argv)

    info = _running()
    if a.cmd == "stop":
        if info:
            try:
                os.kill(info["pid"], 15)
                print("✓ stopped myteam-web (pid {})".format(info["pid"]))
            except OSError as e:
                print("could not stop pid {}: {}".format(info["pid"], e))
        else:
            print("myteam-web is not running")
        return 0
    if info:
        url = "http://127.0.0.1:{}/?t={}".format(info["port"], info["token"])
        print("myteam-web is already running → " + url)
        if a.cmd != "url" and not a.no_browser:
            webbrowser.open(url)
        return 0
    if a.cmd == "url":
        print("myteam-web is not running")
        return 1

    cfg = config.load()
    if cfg is None:
        print("no team yet — run `myteam` once in a terminal to found one")
        return 1
    token = secrets.token_urlsafe(18)
    port = _free_port(a.port)
    hub = Hub(cfg)
    threading.Thread(target=hub.loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(hub, token))
    srv.daemon_threads = True
    config.STATE.mkdir(parents=True, exist_ok=True)
    RUNFILE.write_text(json.dumps({"port": port, "token": token, "pid": os.getpid()}))
    try:
        os.chmod(RUNFILE, 0o600)
    except OSError:
        pass
    url = "http://127.0.0.1:{}/?t={}".format(port, token)
    print("MyTeam web control room for {}".format(cfg["group"]), flush=True)
    print("  → {}".format(url))
    print("  (local only · ctrl-c here or `myteam-web stop` to shut down; your team keeps working)",
          flush=True)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nweb control room closed — the team keeps working.")
    finally:
        try:
            RUNFILE.unlink()
        except OSError:
            pass
    return 0
