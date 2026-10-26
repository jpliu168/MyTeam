"""Manager-led team (DESIGN.md): one named manager, unnamed specialists.

Staffing (add / wake / sleep under a concurrency cap), agent-CLI adapters
with fallback to Claude Code, report-back to the manager, the boss's inbox
(requests + approvals + blocked members), and the learning loop files.
"""
import json
import re
import shlex
import shutil
import time

from . import config, packs, roles

# ---------------------------------------------------------------- prefs
PREFS = {
    "max_active": 3,         # running specialists at once (manager not counted)
    "autonomy": "catalog",   # ask | catalog | full
    "other_clis": True,      # manager may use Codex / Gemini CLI when installed
    "auto_edits": True,      # members start in a no-prompt mode (see `approvals`)
    "approvals": "auto",     # edits = only file edits auto-approved (old behaviour)
                             # auto  = Claude Code auto mode: safe actions run, risky ones still ask
                             # full  = never ask (bypassPermissions) — use with care
}
APPROVALS = ("edits", "auto", "full")


def pref(cfg, key):
    return (cfg.get("prefs") or {}).get(key, PREFS[key])


def set_pref(cfg, key, value):
    if key not in PREFS:
        raise SystemExit("unknown setting '{}' — one of: {}".format(key, ", ".join(PREFS)))
    d = PREFS[key]
    if isinstance(d, bool):
        value = str(value).lower() in ("1", "true", "yes", "on", "y")
    elif isinstance(d, int):
        value = int(value)
    elif key == "autonomy" and value not in ("ask", "catalog", "full"):
        raise SystemExit("autonomy is one of: ask, catalog, full")
    elif key == "approvals" and value not in APPROVALS:
        raise SystemExit("approvals is one of: " + ", ".join(APPROVALS))
    cfg.setdefault("prefs", {})[key] = value
    config.save(cfg)
    return value


# ---------------------------------------------------------------- agent CLIs
CLIS = {
    "claude": {"label": "Claude Code", "bin": "claude",
               "auto": {"edits": "--permission-mode acceptEdits",
                        "auto": "--permission-mode auto",
                        "full": "--permission-mode bypassPermissions"},
               "dirs": lambda ds: "".join(" --add-dir " + shlex.quote(d) for d in ds)},
    "codex": {"label": "Codex", "bin": "codex",
              "auto": {"edits": "--full-auto", "auto": "--full-auto",
                       "full": "--dangerously-bypass-approvals-and-sandbox"},
              "dirs": lambda ds: "".join(" --add-dir " + shlex.quote(d) for d in ds)},
    "gemini": {"label": "Gemini CLI", "bin": "gemini",
               "auto": {"edits": "--approval-mode auto_edit", "auto": "--approval-mode auto_edit",
                        "full": "--approval-mode yolo"},
               "dirs": lambda ds: (" --include-directories " + shlex.quote(",".join(ds)))
               if ds else ""},
}
DEFAULT_CLI = "claude"


def installed_clis():
    return [c for c, a in CLIS.items() if shutil.which(a["bin"])]


def usable_clis(cfg):
    have = installed_clis()
    if not pref(cfg, "other_clis"):
        have = [c for c in have if c == DEFAULT_CLI]
    return have


def pick_cli(cfg, m, wanted=None):
    """(cli, note). Custom members keep their own command."""
    if m.get("agent") == "custom" and not wanted:
        return "custom", ""
    want = wanted or m.get("agent") or DEFAULT_CLI
    if want == "custom":
        return "custom", ""
    if want not in CLIS:
        return DEFAULT_CLI, "unknown CLI '{}' — using Claude Code".format(want)
    if want != DEFAULT_CLI and want not in usable_clis(cfg):
        return DEFAULT_CLI, "{} not available — using Claude Code".format(CLIS[want]["label"])
    return want, ""


def build_cmd(cfg, m, cli):
    """The shell command that launches member m on the given CLI."""
    dirs = config.access_dirs(m)
    if cli == "custom":
        return m["cmd"]
    a = CLIS[cli]
    base = m["cmd"] if (m.get("agent") == cli and m.get("cmd")) else a["bin"]
    flag = a["auto"].get(pref(cfg, "approvals"), a["auto"]["edits"])
    if cli == "claude" and pref(cfg, "auto_edits"):
        # a saved command may still carry the old mode — the team setting wins
        base = re.sub(r"\s--permission-mode[ =]\S+", "", base)
    if pref(cfg, "auto_edits") and flag.split()[0] not in base \
            and "--dangerously" not in base and "--full-auto" not in base:
        base += " " + flag
    return base + a["dirs"](dirs)


# ---------------------------------------------------------------- who is who
MANAGER_ROLES = ("operations-manager", "chief-of-staff", "course-manager", "studio-manager")


def manager_role(cfg):
    lib = roles.for_pack(packs.of(cfg)["id"])
    return next((t["id"] for t in lib if t["id"] in MANAGER_ROLES), "operations-manager")


def manager(cfg):
    name = cfg.get("manager")
    m = config.member(cfg, name) if name else None
    if m is None and name is None:          # older teams: adopt a manager-role member
        hits = [x for x in cfg["members"] if x["role"] in MANAGER_ROLES]
        if len(hits) == 1:
            m = hits[0]
    return m


def is_manager(cfg, m):
    mg = manager(cfg)
    return bool(mg and m and mg["name"] == m["name"])


def specialists(cfg):
    return [m for m in cfg["members"] if not is_manager(cfg, m)]


def set_manager(cfg, m):
    cfg["manager"] = m["name"]
    config.save(cfg)
    from . import skills
    skills.sync(cfg)


def _slug(s):
    return re.sub(r"[^a-z0-9-]+", "-", (s or "").lower()).strip("-")


def specialist_id(cfg, role_id, focus=""):
    base = role_id
    if config.member(cfg, base) and focus:
        base = "{}-{}".format(role_id, "-".join(_slug(focus).split("-")[:2]))
    key, n = base, 2
    while config.member(cfg, key):
        key, n = "{}-{}".format(base, n), n + 1
    return key


# ---------------------------------------------------------------- staffing
def add_specialist(cfg, role_id, focus="", cli=None, nickname="", by="owner",
                   title="", duties=""):
    """Returns (member or None, message). Custom roles may become a request."""
    pid = packs.of(cfg)["id"]
    tpl = roles.by_id(role_id, pid)
    if tpl is None and not duties and by != "owner":
        return None, ("'{}' isn't in the role catalog — give --title and --duties, "
                      "or pick one from `myteam staff`".format(role_id))
    if tpl is None and by != "owner" and pref(cfg, "autonomy") != "full":
        rid = file_request(cfg, "custom-role", "add a custom specialist '{}'".format(role_id),
                           why=duties, by=by,
                           data={"role": role_id, "focus": focus, "title": title,
                                 "duties": duties, "cli": cli or DEFAULT_CLI})
        return None, "custom role needs the boss — request #{} filed".format(rid)
    if by != "owner" and pref(cfg, "autonomy") == "ask":
        rid = file_request(cfg, "add", "add specialist '{}'".format(role_id), why=focus, by=by,
                           data={"role": role_id, "focus": focus, "cli": cli or DEFAULT_CLI})
        return None, "autonomy is 'ask' — request #{} filed for the boss".format(rid)
    key = specialist_id(cfg, _slug(role_id), focus)
    m = {"name": key, "role": _slug(role_id),
         "role_title": tpl["title"] if tpl else (title or role_id),
         "focus": focus, "agent": cli or DEFAULT_CLI, "cmd": CLIS.get(cli or DEFAULT_CLI,
                                                                       CLIS["claude"])["bin"]}
    if nickname:
        m["display"] = nickname
    if tpl is None:
        m["instructions"] = duties
    cfg["members"].append(m)
    config.save(cfg)
    config.member_dir(key)
    _ensure_notebook(m)
    from . import skills
    skills.sync(cfg)
    log_event("added specialist {} ({}){}".format(key, m["role_title"],
              " — focus: " + focus if focus else ""), by=by)
    return m, "added specialist {} — {}".format(key, m["role_title"])


def running_specialists(cfg):
    from . import sessions
    live = set(sessions.list_sessions())
    return [m for m in specialists(cfg) if sessions.sname(m["name"]) in live]


TRUST = re.compile(r"Do you trust|trust this folder|trust the (files|contents)", re.I)
LOGIN = re.compile(r"/login|Please (log|sign) ?in|Login expired|API key|authenticat", re.I)


def wake(cfg, m, task=None, cli=None, by=None, wait=25):
    """Start a member in the background (respecting the cap), clear its CLI's
    first-run folder-trust prompt, fall back to Claude Code if an optional
    CLI fails, then hand over the task. Returns a message."""
    from . import board, bus, sessions, skills
    from .bus import sender_name
    by = by or sender_name()
    name = sessions.sname(m["name"])
    notes = []
    if name not in sessions.list_sessions():
        if not is_manager(cfg, m):
            busy = running_specialists(cfg)
            cap = pref(cfg, "max_active")
            if len(busy) >= cap:
                return ("at the cap ({} running: {}) — `myteam sleep` one that's done, "
                        "or raise it: myteam prefs max_active {}".format(
                            cap, ", ".join(x["name"] for x in busy), cap + 1))
        skills.sync(cfg)
        chosen, note = pick_cli(cfg, m, cli)
        if note:
            notes.append(note)
        sessions.launch(cfg, m, attach=False, cli=chosen)
        outcome = _settle(name, wait)
        if outcome in ("gone", "login") and chosen not in (DEFAULT_CLI, "custom"):
            sessions.kill(name)
            notes.append("{} failed ({}) — fell back to Claude Code".format(
                CLIS[chosen]["label"], outcome))
            sessions.launch(cfg, m, attach=False, cli=DEFAULT_CLI)
            chosen, outcome = DEFAULT_CLI, _settle(name, wait)
        if outcome == "gone":
            time.sleep(0.5)
            why = sessions.last_exit(m["name"])
            return "✗ {} exited right after starting{}".format(
                m["name"], (" — it said:\n" + why) if why else
                " — `myteam start {}` to look".format(m["name"]))
        if outcome == "login":
            notes.append("{} needs a login — the boss must sign in once".format(m["name"]))
        notes.insert(0, "woke {} on {}".format(m["name"], CLIS.get(chosen, {}).get(
            "label", chosen)))
        log_event("woke {} ({})".format(m["name"], chosen), by=by)
    else:
        notes.append("{} already running".format(m["name"]))
    if task:
        tid, note = board.assign(m["name"], task, by=by)
        notes.append("task #{}{}".format(tid, note))
    return "; ".join(notes)


def _settle(name, wait):
    """Give a fresh session a moment; answer the folder-trust prompt (the
    folder is MyTeam's own member folder). Returns idle|working|blocked|login|gone."""
    from . import sessions, status
    deadline, answered = time.time() + wait, False
    time.sleep(2)
    while time.time() < deadline:
        if name not in sessions.list_sessions():
            return "gone"
        lines = sessions.tail(name, 40)
        text = "\n".join(lines[-15:])
        if TRUST.search(text) and not answered:
            _trust_yes(name)
            answered = True
            time.sleep(2)
            continue
        if LOGIN.search(text):
            return "login"
        st = status.classify(lines)
        if st == "idle" and any(l.strip() for l in lines):
            return "idle"
        time.sleep(1.5)
    return status.classify(sessions.tail(name)) if name in sessions.list_sessions() else "gone"


def _trust_yes(name):
    """Answer the CLI's "do you trust this folder?" menu with YES. Newer Claude
    Code puts the cursor on "No, exit", so a bare Enter would quit — move the
    cursor to the yes/trust option first. Falls back to Enter if no menu."""
    from . import sessions
    from .web import choose, find_menu
    menu = find_menu(sessions.tail(name, 60))
    if menu:
        opts = [o.lower() for o in menu["options"]]
        yes = next((i for i, o in enumerate(opts)
                    if ("yes" in o or "trust" in o) and not o.startswith("no")), None)
        if yes is not None and choose(name, yes):
            return
    sessions.send_keys(name, "Enter")


def sleep_member(cfg, m, by=None):
    from . import sessions
    from .bus import sender_name
    name = sessions.sname(m["name"])
    if name not in sessions.list_sessions():
        return "{} is already asleep".format(m["name"])
    sessions.kill(name)
    log_event("put {} to sleep".format(m["name"]), by=by or sender_name())
    return "{} is asleep (folder and notebook kept)".format(m["name"])


def report(cfg, sender, text):
    """Specialist -> manager. Returns a message."""
    from . import brief, bus, sessions
    mg = manager(cfg)
    who = sender[len(sessions.PREFIX):] if sender.startswith(sessions.PREFIX) else sender
    if config.member(cfg, who):
        brief.set_now(who, "reported: " + text[:80])
    if not mg:
        bus.log("owner", sender, text, kind="report")
        return "no manager set — report logged for the boss"
    if who == mg["name"]:
        return "you are the manager — summarize to the boss in your reply instead"
    return bus.deliver(sessions.sname(mg["name"]), text, sender=sender, kind="report")


# ---------------------------------------------------------------- the boss's inbox
def _req_path():
    return config.STATE / "requests.jsonl"


def requests_all():
    p = _req_path()
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _req_write(rows):
    p = _req_path()
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))


KINDS = ("folder", "money", "custom-role", "add", "remove", "public", "other")


def file_request(cfg, kind, what, why="", by="owner", data=None):
    if kind not in KINDS:
        raise SystemExit("request kind is one of: " + ", ".join(KINDS))
    rows = requests_all()
    rid = max([r["id"] for r in rows], default=0) + 1
    rows.append({"id": rid, "ts": round(time.time()), "kind": kind, "what": what,
                 "why": why, "by": by, "status": "pending", "data": data or {}})
    _req_write(rows)
    log_event("request #{} ({}): {}".format(rid, kind, what), by=by)
    return rid


def pending_requests():
    return [r for r in requests_all() if r["status"] == "pending"]


def decide(cfg, rid, approve, note=""):
    """Boss approves / declines. Approved folder, custom-role, add and remove
    requests are carried out here. Returns a message."""
    from . import bus, sessions
    rows = requests_all()
    r = next((x for x in rows if x["id"] == int(rid)), None)
    if not r:
        return "no request #{}".format(rid)
    if r["status"] != "pending":
        return "request #{} is already {}".format(rid, r["status"])
    did = ""
    if approve:
        d = r.get("data") or {}
        try:
            if r["kind"] == "folder":
                m = config.member(cfg, d.get("member", ""))
                folders, bad = config.parse_folders(d.get("folder", ""))
                if not m or bad or not folders:
                    return "can't grant: {}".format("; ".join(bad) or "unknown member")
                m["folders"] = config.member_folders(m) + [
                    f for f in folders if f not in config.member_folders(m)]
                config.save(cfg)
                from . import skills
                skills.sync(cfg)
                did = " — {} can now use {} (from its next start)".format(m["name"], folders[0])
            elif r["kind"] in ("custom-role", "add"):
                m, msg = add_specialist(cfg, d["role"], d.get("focus", ""), d.get("cli"),
                                        by="owner", title=d.get("title", ""),
                                        duties=d.get("duties", ""))
                did = " — " + msg
            elif r["kind"] == "remove":
                from .cli import cmd_retire
                m = config.member(cfg, d.get("member", ""))
                if m:
                    cmd_retire(cfg, m["name"])
                    did = " — {} archived to alumni/".format(m["name"])
        except SystemExit as e:
            return str(e)
    r["status"] = "approved" if approve else "declined"
    r["decided"] = round(time.time())
    if note:
        r["note"] = note
    _req_write(rows)
    msg = "request #{} {}{}".format(rid, r["status"], did)
    mg = manager(cfg)
    if mg:
        bus.deliver(sessions.sname(mg["name"]), "The boss {} request #{} ({}){}{}".format(
            r["status"], rid, r["what"], did, (": " + note) if note else ""),
            sender="owner", kind="decision")
    log_event(msg, by="owner")
    return msg


def inbox_text(cfg):
    from . import bus, sessions, status
    out = []
    reqs = pending_requests()
    if reqs:
        out.append("NEEDS YOUR DECISION")
        for r in reqs:
            out.append("  #{:<3} [{}] {}{}  (from {})".format(
                r["id"], r["kind"], r["what"], " — " + r["why"] if r["why"] else "",
                r["by"].replace(sessions.PREFIX, "")))
        out.append("  → approve <id> · decline <id> [reason]")
    stuck = []
    for name in sessions.list_sessions():
        lines = sessions.tail(name)
        if status.classify(lines) == "blocked":
            stuck.append("  {:<16} {}".format(name[len(sessions.PREFIX):],
                                             status.blocked_reason(lines)[:70]))
    if stuck:
        out.append("WAITING ON A PROMPT (open <member> to answer)")
        out += stuck
    if not out:
        out.append("nothing needs you right now")
    return "\n".join(out)


# ---------------------------------------------------------------- learning loop
def _ensure_notebook(m):
    nb = config.member_dir(m["name"]) / "NOTEBOOK.md"
    if not nb.exists():
        nb.write_text(
            "# Notebook — {} ({})\n\n"
            "Experience notes: read at the start of every job; add 2-5 lines after\n"
            "each one (what worked, what the boss changed, what to do next time).\n"
            "Keep it short — tidy it when it passes ~150 lines.\n\n".format(
                m["name"], m.get("role_title") or m["role"]))
    return nb


def learning_files(cfg):
    hb = config.STATE / "handbook"
    hb.mkdir(parents=True, exist_ok=True)
    pf = hb / "preferences.md"
    if not pf.exists():
        pf.write_text(
            "# The {}'s preferences\n\n"
            "Every correction or standing instruction from the {} goes here, one line\n"
            "each, dated. Everyone reads this before work. Never make the {} say it twice.\n\n"
            .format(packs.of(cfg)["boss"], packs.of(cfg)["boss"], packs.of(cfg)["boss"]))
    rt = hb / "routing.md"
    if not rt.exists():
        rt.write_text(
            "# Which agent CLI for which job (the manager reads this)\n\n"
            "Claude Code is the default for everything. Other CLIs are optional and\n"
            "used only when installed. Edit freely — the manager follows this.\n\n"
            "- default: claude\n"
            "- heavy coding / refactors / scripts: codex is fine\n"
            "- second opinion on a draft: a different CLI than the one that wrote it\n"
            "- Google Docs/Sheets, long web research: gemini is fine\n")
    ll = hb / "learning-log.md"
    if not ll.exists():
        ll.write_text("# What the team learned (newest last)\n\n")
    (config.STATE / "skills").mkdir(parents=True, exist_ok=True)
    for m in cfg["members"]:
        _ensure_notebook(m)


def log_learned(text, by=None):
    from .bus import sender_name
    from . import sessions
    by = (by or sender_name()).replace(sessions.PREFIX, "")
    ll = config.STATE / "handbook" / "learning-log.md"
    ll.parent.mkdir(parents=True, exist_ok=True)
    with open(ll, "a") as f:
        f.write("- {} ({}): {}\n".format(time.strftime("%Y-%m-%d"), by, text))


def learned_since(days=7):
    ll = config.STATE / "handbook" / "learning-log.md"
    if not ll.exists():
        return []
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    out = []
    for l in ll.read_text().splitlines():
        mm = re.match(r"- (\d{4}-\d{2}-\d{2}) ", l)
        if mm and mm.group(1) >= cutoff:
            out.append(l)
    return out


def new_skill(name, description, by=None):
    key = _slug(name)
    d = config.STATE / "skills" / key
    if (d / "SKILL.md").exists():
        return d / "SKILL.md", False
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\nname: {}\ndescription: {}\n---\n\n# {}\n\n"
        "## When to use\n\n## Steps\n\n1. \n\n## Gotchas (from real jobs)\n\n"
        "## Examples\n\n".format(key, description.replace("\n", " "), name))
    log_learned("new team skill '{}': {}".format(key, description), by=by)
    return d / "SKILL.md", True


# ---------------------------------------------------------------- activity log
def log_event(text, by="owner"):
    from . import sessions
    p = config.STATE / "activity.log"
    with open(p, "a") as f:
        f.write("{} {}: {}\n".format(time.strftime("%Y-%m-%d %H:%M"),
                                     str(by).replace(sessions.PREFIX, ""), text))


# ---------------------------------------------------------------- staff view
def staff_text(cfg):
    from . import sessions, status
    live = set(sessions.list_sessions())
    pid = packs.of(cfg)["id"]
    mg = manager(cfg)
    out = []
    if mg:
        st = "running" if sessions.sname(mg["name"]) in live else "asleep"
        out.append("MANAGER   {} — {} [{}]".format(config.display(mg),
                                                    mg.get("role_title") or mg["role"], st))
    else:
        out.append("MANAGER   (none — `myteam manager <member>` or re-run setup)")
    sp = specialists(cfg)
    out.append("SPECIALISTS ({} running / cap {})".format(
        len([m for m in sp if sessions.sname(m["name"]) in live]), pref(cfg, "max_active")))
    for m in sp:
        name = sessions.sname(m["name"])
        st = status.classify(sessions.tail(name)) if name in live else "asleep"
        nick = " “{}”".format(m["display"]) if m.get("display") else ""
        out.append("  {:<20} {:<9} {}{}{}".format(
            m["name"], st, m.get("role_title") or m["role"], nick,
            " — " + m["focus"] if m.get("focus") else ""))
    if not sp:
        out.append("  (none yet — add from the catalog below)")
    have = {m["role"] for m in sp}
    out.append("CATALOG ({} preset) — myteam add <role> [\"focus\"]".format(pid))
    for t in roles.for_pack(pid):
        if t["id"] in MANAGER_ROLES:
            continue
        out.append("  {}{:<24} {}".format("·" if t["id"] in have else " ", t["id"], t["title"]))
    out.append("CLIs usable now: {}  (autonomy: {}, auto-edits: {})".format(
        ", ".join(CLIS[c]["label"] for c in usable_clis(cfg)) or "none found!",
        pref(cfg, "autonomy"),
        pref(cfg, "approvals") if pref(cfg, "auto_edits") else "off"))
    return "\n".join(out)
