"""`myteam` — the owner's one command."""
import shutil
import sys
import time

from . import board, bus, config, daemon, roles, sessions, status, wizard

HELP = """\
myteam — your group of agents: one owner, many roles

  myteam                     first run: found your team; after: THE CONTROL ROOM —
                            talk to any member ("sam: ..."), broadcast ("@all ..."),
                            assign tasks, watch agents talk to each other
  myteam plain               the control room as a plain prompt (no full-screen UI)
  myteam web                 the control room in your browser (same as `myteam-web`)
  myteam roster              org chart: members, roles, focus, live status
  myteam up                  raise the whole team: every member + the daemon, in the background
  myteam start <member>      start (or resume) a member's session and attach
  myteam office              ALL members as tabs in one terminal (ctrl-b n/p to switch)
  myteam attach <member>     attach to a running member
  myteam ls                  running members with status ● working ◐ blocked ○ idle
  myteam standup             the morning view: statuses, tasks, fresh deliverables
  myteam brief               one line per member: what each is doing right now
  myteam now "text"          (for members) set your one-line "what I'm doing" note

  myteam hire                add a member        myteam edit <m>    change a role card
  myteam retire <m>          archive a member (workspace kept in alumni/)

  myteam assign <m> "task"   put a task on the board (+notify the member)
  myteam tasks [m]           open tasks          myteam done <id>   mark finished

  myteam log [m] [-n N]      communication history (all bus traffic, or one member's)
  myteam msg <m> "text"      message a member (queued politely if busy)
  myteam ask <m> "text"      ask and wait for the reply
  myteam deliver [m]         flush queued messages to idle members now
  myteam wait <m> | status <m> | kill <m>

  myteam daemon start|run|status    the mailman/status-watcher (tmux session)
  myteam skills sync         re-render shared skills + role cards for everyone
  myteam config              show config path and contents
"""


def _need_cfg():
    cfg = config.load()
    if cfg is None:
        print("no team yet — run `myteam` to found one")
        sys.exit(1)
    return cfg


def _member(cfg, token):
    m = config.member(cfg, token)
    if m:
        return m
    tl = token.lower()
    hits = [x for x in cfg["members"]
            if tl == config.display(x).lower() or tl == x["name"]
            or tl in x["name"] or tl in config.display(x).lower()]
    # exact display/key match wins over substring
    exact = [x for x in hits if tl in (x["name"], config.display(x).lower())]
    hits = exact or hits
    if len(hits) == 1:
        return hits[0]
    raise SystemExit("no member '{}' (myteam roster)".format(token))


def cmd_roster(cfg):
    live = sessions.list_sessions()
    print("═══ {} ═══".format(cfg["group"]))
    if not cfg["members"]:
        print("no members yet — `myteam hire`")
        return 0
    for m in cfg["members"]:
        name = sessions.sname(m["name"])
        if name in live:
            st = status.classify(sessions.tail(name))
            tag = "{} {}".format(status.GLYPH[st], st)
        else:
            tag = "  not running"
        print("  {:<12} {:<18} [{}]  {:<14} {}".format(
            config.display(m), m["role"], m["agent"], tag, (m.get("focus") or "")[:48]))
    return 0


def cmd_ls(cfg):
    live = sessions.list_sessions()
    if not live:
        print("no members running — `myteam start <member>`")
        return 0
    for name in live:
        lines = sessions.tail(name, 30)
        st = status.classify(lines)
        last = lines[-1][:70] if lines else ""
        print("{:<24} {} {:<8} {}".format(name, status.GLYPH[st], st, last))
    return 0


def _rename_member(cfg, m, new_display):
    """Rename a member. A pure case/display change keeps the internal key and
    just sets `display` (safe on case-insensitive filesystems). A change to a
    different word moves the workspace, bus files, and task ownership."""
    import re
    new_slug = re.sub(r"[^a-z0-9-]+", "-", new_display.lower()).strip("-")
    old = m["name"]
    if not new_slug or new_slug == old:
        m["display"] = new_display            # display-only (e.g. sam -> Sam)
        return old
    if config.member(cfg, new_slug):
        print("  a member keyed '{}' already exists — pick another name".format(new_slug))
        return old
    # real rename: stop session, move dir + bus files, reassign tasks
    if sessions.sname(old) in sessions.list_sessions():
        sessions.kill(sessions.sname(old))
    import shutil
    olddir, newdir = config.STATE / "members" / old, config.STATE / "members" / new_slug
    if olddir.exists():
        shutil.move(str(olddir), str(newdir))
    busdir = config.STATE / "bus"
    if busdir.exists():
        for f in busdir.glob("{}.*".format(sessions.sname(old))):
            f.rename(busdir / f.name.replace(sessions.sname(old), sessions.sname(new_slug)))
    board.reassign_owner(old, new_slug)
    m["name"] = new_slug
    m["display"] = new_display
    return new_slug


def cmd_edit(cfg, token):
    m = _member(cfg, token)
    print("editing {} — press enter to keep the current value".format(config.display(m)))
    new_name = wizard.ask("display name", config.display(m))
    if new_name and new_name != config.display(m):
        _rename_member(cfg, m, new_name)
        print("  ✓ now shown as '{}'".format(config.display(m)))
    from . import packs
    lib = roles.for_pack(packs.of(cfg)["id"])
    menu = roles.menu(packs.of(cfg)["id"])
    i = wizard.choose("role? (current: {})".format(m["role"]),
                      menu + ["(keep current)"], default=len(menu) + 1)
    if i < len(lib):
        m["role"], m["role_title"] = lib[i]["id"], lib[i]["title"]
        m.pop("instructions", None)
    elif i == len(lib):
        m["role"] = wizard.ask("custom role id", m["role"])
        m["role_title"] = wizard.ask("role title", m.get("role_title", ""))
        m["instructions"] = wizard.ask("duties (one paragraph)",
                                       m.get("instructions", ""))
    m["focus"] = wizard.ask("focus", m.get("focus") or "")
    cmd = wizard.ask("launch command", m["cmd"])
    if cmd != m["cmd"]:
        m["cmd"] = cmd
        m["agent"] = cmd if cmd in ("claude", "codex") else "custom"
    folders = wizard.ask_folders(m, config.member_folders(m))
    if folders:
        m["folders"] = folders
    else:
        m.pop("folders", None)
    config.save(cfg)
    from . import skills
    skills.sync(cfg)
    print("✓ saved (takes effect on {}'s next session start)".format(m["name"]))
    return 0


def cmd_retire(cfg, token, purge=False):
    m = _member(cfg, token)
    name = sessions.sname(m["name"])
    if name in sessions.list_sessions():
        sessions.kill(name)
    n = board.unassign_member(m["name"])
    cfg["members"] = [x for x in cfg["members"] if x["name"] != m["name"]]
    config.save(cfg)
    mdir = config.member_dir(m["name"])
    if purge:
        shutil.rmtree(mdir, ignore_errors=True)
        print("✓ {} retired and purged".format(m["name"]))
    else:
        alumni = config.STATE / "alumni"
        alumni.mkdir(parents=True, exist_ok=True)
        dest = alumni / "{}-{}".format(m["name"], time.strftime("%Y%m%d"))
        shutil.move(str(mdir), str(dest))
        print("✓ {} retired — workspace archived to {}".format(m["name"], dest))
    if n:
        print("  {} open task(s) returned to the pool (owner: unassigned)".format(n))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        cfg = config.load()
        if cfg is None:
            wizard.first_run()
            return 0
        import sys as _sys
        if _sys.stdin.isatty():
            try:
                from . import tui
                return tui.room(cfg)
            except Exception:
                pass  # terminal can't do curses — plain console below
        from . import control
        return control.room(cfg)
    cmd, args = argv[0], argv[1:]
    if cmd == "web":
        from . import web
        return web.main(args)
    if cmd == "plain":
        cfg = _need_cfg()
        from . import control
        return control.room(cfg)
    if cmd in ("-h", "--help", "help"):
        print(HELP)
        return 0
    cfg = _need_cfg()
    if cmd == "roster":
        return cmd_roster(cfg)
    if cmd == "ls":
        return cmd_ls(cfg)
    if cmd == "brief":
        sts = {}
        live = sessions.list_sessions()
        for m in cfg["members"]:
            sn = sessions.sname(m["name"])
            sts[m["name"]] = status.classify(sessions.tail(sn)) if sn in live else "off"
        from . import brief
        print(brief.text_report(cfg, sts))
        return 0
    if cmd == "now":
        import os
        from . import brief
        who = os.environ.get("MYTEAM_MEMBER")
        if args and args[0] == "--as" and len(args) >= 3:
            who, args = _member(cfg, args[1])["name"], args[2:]
        if not who:
            raise SystemExit("run this inside a member session, or: myteam now --as <member> \"text\"")
        brief.set_now(who, " ".join(args))
        print("✓ {} is now: {}".format(who, " ".join(args) or "(cleared)"))
        return 0
    if cmd == "standup":
        print(board.standup(cfg))
        return 0
    if cmd == "up":
        if not sessions.tmux_ok():
            print("`myteam up` needs tmux (conda install -c conda-forge tmux)")
            return 1
        live = sessions.list_sessions()
        for m in cfg["members"]:
            name = sessions.sname(m["name"])
            if name in live:
                print("  = {} already running".format(m["name"]))
            else:
                sessions.launch(cfg, m, attach=False)
                print("  ✓ {} started ({})".format(m["name"], m["role"]))
        me = config.root() / "bin" / "myteam"
        if sessions.run_daemon_session('"{}" daemon run'.format(me)):
            print("  ✓ daemon started")
        else:
            print("  = daemon already running")
        print("team is up — `myteam ls` for statuses, `myteam attach <m>` to visit,")
        print("note: a member's FIRST ever start may sit ◐ blocked on its CLI's")
        print("trust prompt — `myteam attach <m>` once to answer it.")
        return 0
    if cmd == "office":
        name = sessions.build_office()
        print("office open — tabs: ctrl-b n (next) / ctrl-b p (prev) / ctrl-b <number>; leave: ctrl-b d")
        sessions.attach_to(name)
        return 0
    if cmd == "start" and args:
        m = _member(cfg, args[0])
        print("starting {} ({}) — detach: ctrl-b d, it keeps running".format(
            m["name"], m.get("role_title") or m["role"]))
        sessions.launch(cfg, m)
        return 0
    if cmd == "attach" and args:
        sessions.attach_to(sessions.resolve(args[0]))
        return 0
    if cmd == "hire":
        wizard.hire(cfg)
        config.save(cfg)
        from . import skills
        skills.sync(cfg)
        return 0
    if cmd == "edit" and args:
        return cmd_edit(cfg, args[0])
    if cmd == "retire" and args:
        return cmd_retire(cfg, args[0], purge="--purge" in args)
    if cmd == "assign" and len(args) >= 2:
        m = _member(cfg, args[0])
        tid, note = board.assign(m["name"], " ".join(args[1:]),
                                 by=bus.sender_name())
        print("task #{} -> {}{}".format(tid, m["name"], note))
        return 0
    if cmd == "tasks":
        owner = _member(cfg, args[0])["name"] if args else None
        for t in board.listing(owner):
            print("#{:<3} [{:<10}] {:<8} {}".format(
                t["id"], t["owner"][:10], t["status"], t["task"]))
        return 0
    if cmd == "done" and args:
        t = board.set_status(args[0], "done")
        print("✓ task #{} done: {}".format(t["id"], t["task"]) if t
              else "no task #{}".format(args[0]))
        return 0
    if cmd == "log":
        import json as _json
        import time as _time
        n = 40
        member_filter = None
        for a in args:
            if a == "-n":
                continue
            if a.isdigit():
                n = int(a)
            else:
                member_filter = a
        recs = []
        busdir = config.STATE / "bus"
        if busdir.exists():
            for f in busdir.glob("*.log.jsonl"):
                for line in f.read_text().splitlines():
                    try:
                        recs.append(_json.loads(line))
                    except ValueError:
                        pass
        short = lambda s: s[len(sessions.PREFIX):] if s.startswith(sessions.PREFIX) else s
        if member_filter:
            recs = [r for r in recs if member_filter in short(r.get("from", ""))
                    or member_filter in short(r.get("to", ""))]
        recs.sort(key=lambda r: r.get("ts", 0))
        for r in recs[-n:]:
            t = _time.strftime("%m-%d %H:%M", _time.localtime(r.get("ts", 0)))
            text = r.get("text", "").replace("\n", " ")
            print("{} {:>8} → {:<8} [{}] {}".format(
                t, short(r.get("from", "?"))[:8], short(r.get("to", "?"))[:8],
                r.get("kind", "msg"), text[:110] + ("…" if len(text) > 110 else "")))
        if not recs:
            print("no bus traffic yet")
        return 0
    if cmd == "msg" and len(args) >= 2:
        to = sessions.sname(_member(cfg, args[0])["name"])
        print("→ {}".format(bus.deliver(to, " ".join(args[1:]))))
        return 0
    if cmd == "ask" and len(args) >= 2:
        to = sessions.resolve(args[0])
        print("asking {} … (waits politely, then for the answer)".format(to))
        reply, outcome = bus.ask(to, " ".join(args[1:]))
        if reply is not None:
            print("─" * 60 + "\n" + reply + "\n" + "─" * 60)
            return 0
        print("no reply: {} (try `myteam attach {}`)".format(outcome, args[0]))
        return 1
    if cmd == "deliver":
        targets = [sessions.sname(_member(cfg, args[0])["name"])] if args \
            else sessions.list_sessions()
        total = sum(bus.flush(t) for t in targets)
        print("delivered {} queued message(s)".format(total))
        return 0
    if cmd == "wait" and args:
        print(bus.wait_idle(sessions.resolve(args[0])))
        return 0
    if cmd == "status" and args:
        name = sessions.resolve(args[0])
        st = bus.current_status(name)
        print("{} {} {}".format(name, status.GLYPH.get(st, "?"), st))
        return 0
    if cmd == "kill" and args:
        sessions.kill(sessions.resolve(args[0]))
        return 0
    if cmd == "daemon":
        sub = args[0] if args else "status"
        if sub == "run":
            daemon.run()
            return 0
        if sub == "start":
            me = config.root() / "bin" / "myteam"
            started = sessions.run_daemon_session('"{}" daemon run'.format(me))
            print("daemon started (tmux session myteam-daemon)" if started
                  else "daemon already running")
            return 0
        live = sessions.DAEMON in sessions.list_sessions(include_daemon=True)
        print("daemon: {}".format("running" if live else "not running"))
        return 0
    if cmd == "skills" and args and args[0] == "sync":
        from . import skills
        n = skills.sync(cfg)
        print("rendered {} skill(s) per member for {} member(s)".format(
            n, len(cfg["members"])))
        return 0
    if cmd == "config":
        print(config.CONFIG)
        if config.CONFIG.exists():
            print(config.CONFIG.read_text())
        return 0
    print(HELP)
    return 1
