"""`myteam` — the owner's one command."""
import shutil
import sys
import time

from . import board, bus, config, daemon, roles, sessions, status, wizard

HELP = """\
myteam — one manager runs your team of specialist agents; you talk to the manager

  myteam                     the control room: just type — it goes to your manager
                            (advanced: "@bookkeeper ..." talks to a specialist directly)
  myteam web                 the control room in your browser
  myteam inbox               what needs YOU: requests to approve, members stuck on a prompt
  myteam approve <id> | decline <id> ["reason"]
  myteam up                  start the manager + the daemon (specialists wake on demand)
  myteam staff               manager, specialists (running/asleep), role catalog, CLIs
  myteam brief | standup     what everyone is doing / the morning view
  myteam learned [days]      what the team learned recently (default 7 days)

 setup
  myteam hire                add a specialist (or `myteam add <role> ["focus"]`)
  myteam manager <member>    make <member> the manager
  myteam edit <m> | retire <m>
  myteam prefs [key value]   max_active · autonomy (ask|catalog|full) · other_clis · auto_edits

 used by the manager (you can too)
  myteam add <role> ["focus"] [--cli codex] [--nick Lily]
  myteam wake <s> ["task"] [--cli claude|codex|gemini]     myteam sleep <s>
  myteam assign <m> "task" · tasks [m] · done <id>
  myteam request <kind> "what" ["why"] [--member m --folder path]
        kinds: folder money public custom-role add remove other
  myteam skill new <name> "description"     myteam skills sync
  myteam learned "what changed"

 used by specialists
  myteam report "done #12: ... in deliverables/..."    myteam now "what I'm doing"

 plumbing
  myteam start|attach <m> · office · ls · roster · log [m] · msg|ask <m> "text"
  myteam deliver [m] · wait|status|kill <m> · daemon start|run|status · config
"""


TEAM_CMDS = ("staff", "add", "wake", "sleep", "report", "request", "inbox", "approve",
             "decline", "learned", "skill", "prefs", "manager")


def _flags(args, names):
    """Split --name value flags out of args. Returns (positional, {name: value})."""
    pos, fl, i = [], {}, 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and a[2:] in names and i + 1 < len(args):
            fl[a[2:]] = args[i + 1]
            i += 2
            continue
        pos.append(a)
        i += 1
    return pos, fl


def team_cmd(cmd, args):
    from . import team, bus
    cfg = _need_cfg()
    me = bus.sender_name()
    if cmd == "staff":
        print(team.staff_text(cfg))
        return 0
    if cmd == "inbox":
        print(team.inbox_text(cfg))
        return 0
    if cmd in ("approve", "decline"):
        if not args:
            print("usage: myteam {} <id> [reason]".format(cmd))
            return 1
        if me != "owner":
            print("only the boss decides requests")
            return 1
        print(team.decide(cfg, args[0], cmd == "approve", " ".join(args[1:])))
        return 0
    if cmd == "manager":
        if not args:
            mg = team.manager(cfg)
            print("manager: {}".format(config.display(mg) if mg else "(none)"))
            return 0
        m = _member(cfg, args[0])
        team.set_manager(cfg, m)
        print("✓ {} is the manager — plain messages in the control room now go to them".format(
            config.display(m)))
        return 0
    if cmd == "add":
        pos, fl = _flags(args, ("cli", "nick", "title", "duties"))
        if not pos:
            print(team.staff_text(cfg))
            print("\nusage: myteam add <role> [\"focus\"] [--cli codex] [--nick Lily]")
            return 1
        m, msg = team.add_specialist(cfg, pos[0], " ".join(pos[1:]), fl.get("cli"),
                                     fl.get("nick", ""), by=me, title=fl.get("title", ""),
                                     duties=fl.get("duties", ""))
        print(("✓ " if m else "→ ") + msg)
        return 0
    if cmd == "wake":
        pos, fl = _flags(args, ("cli",))
        if not pos:
            print("usage: myteam wake <specialist> [\"task\"] [--cli codex]")
            return 1
        m = _member(cfg, pos[0])
        print(team.wake(cfg, m, " ".join(pos[1:]) or None, fl.get("cli")))
        return 0
    if cmd == "sleep":
        if not args:
            print("usage: myteam sleep <specialist> | all")
            return 1
        targets = (team.running_specialists(cfg) if args[0] == "all"
                   else [_member(cfg, args[0])])
        for m in targets:
            if team.is_manager(cfg, m):
                print("not putting the manager to sleep (use `myteam kill`)")
                continue
            print(team.sleep_member(cfg, m))
        return 0
    if cmd == "report":
        if not args:
            print('usage: myteam report "done #12: ... in deliverables/..."')
            return 1
        print(team.report(cfg, me, " ".join(args)))
        return 0
    if cmd == "request":
        pos, fl = _flags(args, ("member", "folder"))
        if len(pos) < 2:
            print('usage: myteam request <kind> "what" ["why"] [--member m --folder path]')
            print("kinds: " + ", ".join(team.KINDS))
            return 1
        data = {}
        if pos[0] == "folder":
            if not fl.get("folder"):
                print("folder requests need --folder <path> (and --member <who>)")
                return 1
            data = {"folder": fl["folder"], "member": fl.get("member") or me.replace(
                sessions.PREFIX, "")}
        elif pos[0] == "remove":
            data = {"member": fl.get("member", "")}
        rid = team.file_request(cfg, pos[0], pos[1], " ".join(pos[2:]), by=me, data=data)
        print("request #{} filed — the boss sees it in `myteam inbox`".format(rid))
        return 0
    if cmd == "learned":
        if args and not args[0].isdigit():
            team.log_learned(" ".join(args))
            print("✓ logged in handbook/learning-log.md")
            return 0
        rows = team.learned_since(int(args[0]) if args else 7)
        print("\n".join(rows) if rows else "nothing logged in that period")
        return 0
    if cmd == "skill":
        if len(args) >= 3 and args[0] == "new":
            path, created = team.new_skill(args[1], " ".join(args[2:]))
            if created:
                from . import skills
                skills.sync(cfg)
            print("{} {} — fill in the steps, then `myteam skills sync`".format(
                "✓ created" if created else "= exists:", path))
            return 0
        print('usage: myteam skill new <name> "description"')
        return 1
    if cmd == "prefs":
        if len(args) >= 2:
            v = team.set_pref(cfg, args[0], args[1])
            print("✓ {} = {}".format(args[0], v))
        else:
            for k in team.PREFS:
                print("  {:<12} {}".format(k, team.pref(cfg, k)))
        return 0
    return 1


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
    if cfg.get("manager") == old:
        cfg["manager"] = new_slug
    m["name"] = new_slug
    m["display"] = new_display
    return new_slug


def cmd_edit(cfg, token):
    m = _member(cfg, token)
    print("editing {} — press enter to keep the current value".format(config.display(m)))
    from . import team
    if team.is_manager(cfg, m):
        new_name = wizard.ask("manager's name", config.display(m))
        if new_name and new_name != config.display(m):
            _rename_member(cfg, m, new_name)
    else:
        nick = wizard.ask("nickname (optional, '-' to clear)", m.get("display") or "")
        if nick == "-":
            m.pop("display", None)
        elif nick:
            m["display"] = nick
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
    if cmd in TEAM_CMDS:
        return team_cmd(cmd, args)
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
        from . import team
        mg = team.manager(cfg)
        for m in ([mg] if mg else cfg["members"]):
            name = sessions.sname(m["name"])
            if name in live:
                print("  = {} already running".format(m["name"]))
            else:
                print("  ✓ " + team.wake(cfg, m))
        me = config.root() / "bin" / "myteam"
        if sessions.run_daemon_session('"{}" daemon run'.format(me)):
            print("  ✓ daemon started")
        else:
            print("  = daemon already running")
        print("team is up — your manager is in; specialists wake when the manager needs them."
              if mg else "team is up — tip: `myteam manager <member>` to run the team through one manager.")
        print("talk to them: `myteam` (or `myteam web`) · what needs you: `myteam inbox`")
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
