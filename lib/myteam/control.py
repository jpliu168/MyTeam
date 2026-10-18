"""The control room — `myteam` with no arguments drops the owner here.

One terminal, chat-style:
    sam: draft the aims page          talk to a member (also: @sam ...)
    @all stand by for new priorities  broadcast to every member
    assign david "make the deck"      task board + notify
    watch on|off                      stream agent-to-agent bus traffic
    open sam                          full-screen into sam (ctrl-b d returns)
    roster / ls / standup / tasks     the usual views
    quit                              leave (members keep working)

A background watcher prints members' replies when they finish, flushes the
polite-delivery queue (so the control room works even without the daemon),
and — when watch is on — shows every message agents send each other.
"""
import json
import sys
import threading
import time

from . import board, bus, config, sessions, status

POLL = 2.0


def _say(line):
    sys.stdout.write("\r\033[K" + line + "\nyou> ")
    sys.stdout.flush()


class Watcher(threading.Thread):
    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.watch_traffic = True
        self.paused = False
        self.awaiting = {}          # session name -> time sent
        self._offsets = {}          # bus log file -> bytes read
        self._prime_offsets()

    def _prime_offsets(self):
        d = config.STATE / "bus"
        if d.exists():
            for f in d.glob("*.log.jsonl"):
                self._offsets[f] = f.stat().st_size

    def expect_reply(self, name):
        self.awaiting[name] = time.time()

    def _new_traffic(self):
        d = config.STATE / "bus"
        if not d.exists():
            return
        for f in sorted(d.glob("*.log.jsonl")):
            pos = self._offsets.get(f, 0)
            size = f.stat().st_size
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
                if not frm.startswith(sessions.PREFIX):
                    continue  # owner's own messages — no need to echo
                if self.watch_traffic:
                    short = lambda s: s[len(sessions.PREFIX):] if s.startswith(sessions.PREFIX) else s
                    text = rec.get("text", "")
                    _say("  ⇄ {} → {} [{}]: {}".format(
                        short(frm), short(rec.get("to", "?")), rec.get("kind", "msg"),
                        text[:140] + ("…" if len(text) > 140 else "")))

    def _replies(self):
        for name, sent in list(self.awaiting.items()):
            if time.time() - sent < 6:
                continue
            st = bus.current_status(name)
            if st == "idle":
                tail = sessions.tail(name, 14)
                del self.awaiting[name]
                short = name[len(sessions.PREFIX):]
                block = ["── {} ──────────────────────────────".format(short)]
                block += ["  " + l for l in tail]
                block.append("── end {0} (open {0} for the full screen) ──".format(short))
                _say("\n".join(block))
            elif st == "gone":
                del self.awaiting[name]
                _say("  ✗ {} exited — `open {}` to investigate".format(name, name))

    def run(self):
        while True:
            if not self.paused:
                try:
                    for name in sessions.list_sessions():
                        bus.flush(name)          # stand-in mailman
                    self._new_traffic()
                    self._replies()
                except Exception:
                    pass
            time.sleep(POLL)


def _target(cfg, token):
    m = config.member(cfg, token)
    if m is None:
        hits = [x for x in cfg["members"] if token in x["name"]]
        m = hits[0] if len(hits) == 1 else None
    return m


def _send(cfg, watcher, member, text):
    name = sessions.sname(member["name"])
    if name not in sessions.list_sessions():
        sessions.launch(cfg, member, attach=False)
        print("  (started {} in the background)".format(member["name"]))
        time.sleep(1)
    outcome = bus.deliver(name, text, sender="owner")
    watcher.expect_reply(name)
    print("  → {}: {}".format(member["name"], outcome))


def room(cfg):
    print("═══ {} — control room ═══".format(cfg["group"]))
    print("members: " + ", ".join(m["name"] for m in cfg["members"]))
    print('talk: "sam: <message>" or "@sam <message>" · everyone: "@all <message>"')
    print('assign <m> <task> · watch on|off (agent↔agent traffic, now ON) · open <m>')
    print("roster · ls · standup · tasks · quit (members keep working)")
    watcher = Watcher(cfg)
    watcher.start()
    from .cli import cmd_roster, cmd_ls
    while True:
        try:
            raw = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nleaving the control room — the team keeps working. bye.")
            return 0
        if not raw:
            continue
        cmd = raw.split()[0].lower().rstrip(":")
        rest = raw[len(raw.split()[0]):].strip()
        if cmd in ("quit", "exit", "q"):
            print("leaving the control room — the team keeps working. bye.")
            return 0
        if cmd == "watch":
            watcher.watch_traffic = rest.lower() != "off"
            print("  agent↔agent traffic: {}".format("ON" if watcher.watch_traffic else "off"))
            continue
        if cmd == "roster":
            cmd_roster(cfg)
            continue
        if cmd == "ls":
            cmd_ls(cfg)
            continue
        if cmd == "standup":
            print(board.standup(cfg))
            continue
        if cmd == "tasks":
            for t in board.listing():
                print("  #{:<3} [{:<10}] {:<8} {}".format(
                    t["id"], t["owner"][:10], t["status"], t["task"]))
            continue
        if cmd == "done" and rest:
            t = board.set_status(rest.split()[0], "done")
            print("  ✓ done" if t else "  no such task")
            continue
        if cmd == "assign" and rest:
            parts = rest.split(None, 1)
            m = _target(cfg, parts[0]) if parts else None
            if m and len(parts) == 2:
                tid, note = board.assign(m["name"], parts[1].strip('"'), by="owner")
                watcher.expect_reply(sessions.sname(m["name"]))
                print("  task #{} -> {}{}".format(tid, m["name"], note))
            else:
                print("  usage: assign <member> <task>")
            continue
        if cmd == "open" and rest:
            m = _target(cfg, rest.split()[0])
            if m:
                watcher.paused = True
                sessions.attach_to(sessions.sname(m["name"]))
                watcher.paused = False
                print("(back in the control room)")
            else:
                print("  no member '{}'".format(rest))
            continue
        # talk: "@sam text" | "@sam @david text" | "@all text" | "sam: text"
        if raw.startswith("@"):
            words = raw.split()
            mentions, rest_words = [], []
            for i, w in enumerate(words):
                if w.startswith("@") and not rest_words:
                    mentions.append(w[1:].rstrip(",:"))
                else:
                    rest_words = words[i:]
                    break
            text = " ".join(rest_words).strip()
            if not text:
                print("  say something after the @mentions")
                continue
            if any(t.lower() == "all" for t in mentions):
                targets = cfg["members"]
            else:
                targets, bad = [], []
                for t in mentions:
                    m = _target(cfg, t)
                    (targets.append(m) if m else bad.append(t))
                if bad:
                    print("  no member: {}".format(", ".join(bad)))
            seen = set()
            for m in targets:
                if m["name"] not in seen:
                    seen.add(m["name"])
                    _send(cfg, watcher, m, text)
            continue
        m = _target(cfg, cmd)
        if m and rest:
            _send(cfg, watcher, m, rest)
            continue
        print('  not understood — "sam: <message>", "@all <message>", assign, watch on|off,')
        print("  open <m>, roster, ls, standup, tasks, done <id>, quit")
