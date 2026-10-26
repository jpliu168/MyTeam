"""First-run onboarding ("found your team") and the hiring mini-wizard."""
import re
import shutil

from . import config, packs, roles

BANNER = r"""
  __  __       _____
 |  \/  |_   _|_   _|__  __ _ _ __ ___    your team · your agents
 | |\/| | | | || |/ _ \/ _` | '_ ` _ \    you · one manager · specialists
 | |  | | |_| || |  __/ (_| | | | | | |
 |_|  |_|\__, ||_|\___|\__,_|_| |_| |_|   forked from MyLab
         |___/
"""

AGENT_CLIS = [("claude", "Claude Code"), ("codex", "Codex"),
              ("custom", "another agent CLI (type the command)")]


def ask(prompt, default=None):
    sfx = " [{}]".format(default) if default else ""
    try:
        val = input("{}{}: ".format(prompt, sfx)).strip()
    except EOFError:
        val = ""
    return val or (default or "")


def choose(prompt, options, default=1):
    print(prompt)
    for i, o in enumerate(options, 1):
        print("  {}) {}".format(i, o))
    while True:
        v = ask("choice", str(default))
        if v.isdigit() and 1 <= int(v) <= len(options):
            return int(v) - 1
        print("  please enter a number between 1 and {}".format(len(options)))


def _slug(s):
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-") or "member"


def ask_folders(m, current=None):
    """Ask for extra folders; re-asks until every path is valid. Returns list."""
    print("  working folder: {}  (always)".format(config.member_dir(m["name"])))
    print("  shared team folders: deliverables/, handbook/, bus/  (always)")
    hint = "extra folders {} can use — comma-separated, blank for none".format(
        config.display(m))
    if current:
        hint += ", '-' to clear"
    while True:
        text = ask(hint, ", ".join(current) if current else "")
        folders, bad = config.parse_folders(text)
        if not bad:
            return folders
        for b in bad:
            print("  ✗ " + b)


def hire(cfg):
    """Add one specialist interactively (role + focus; a nickname is optional).
    Returns the member dict or None."""
    from . import team
    print("\n-- Add a specialist --  (no name needed: a role + a focus)")
    pid = packs.of(cfg)["id"]
    lib = [t for t in roles.for_pack(pid) if t["id"] not in team.MANAGER_ROLES]
    i = choose("role?", ["{} — {}".format(t["id"], t["title"]) for t in lib]
               + ["custom — define your own role"])
    custom_instructions = ""
    if i < len(lib):
        role, role_title = lib[i]["id"], lib[i]["title"]
    else:
        role = _slug(ask("custom role id (e.g. field-work)"))
        if not role:
            return None
        role_title = ask("one-line role title")
        custom_instructions = ask("describe the role's duties (one paragraph)")
    focus = ask("focus (one sentence, or blank)", "")
    nick = ask("nickname (optional — blank is fine)", "")
    cid, cmd = "claude", "claude"
    extra = [c for c in team.installed_clis() if c != "claude"]
    if extra:
        opts = [("claude", "Claude Code (default)")] + [(c, team.CLIS[c]["label"]) for c in extra] \
            + [("custom", "another agent CLI (type the command)")]
        j = choose("default agent CLI? (the manager can still pick per job)",
                   [l for _, l in opts])
        cid = opts[j][0]
        cmd = team.CLIS[cid]["bin"] if cid != "custom" else ask("command to launch it")
        if not cmd:
            return None
    name = team.specialist_id(cfg, role, focus)
    m = {"name": name, "role": role, "role_title": role_title, "focus": focus,
         "agent": cid, "cmd": cmd}
    if nick:
        m["display"] = nick
    if custom_instructions:
        m["instructions"] = custom_instructions
    folders = ask_folders(m)
    if folders:
        m["folders"] = folders
    cfg["members"].append(m)
    print("  ✓ added {} ({}) — working folder {}".format(
        name, role_title, config.member_dir(name)))
    return m


def make_manager(cfg):
    """Ask for the manager's name; create the manager member. Returns it."""
    from . import team
    boss = packs.of(cfg)["boss"]
    print("\nYour manager is the one agent you talk to. They run the team for you:")
    print("they bring in specialists when a job needs them and report back to you.")
    display = ""
    while not display:
        display = ask("Name your manager (e.g. Alex)", "Alex").strip()
    key = _slug(display)
    if not key or config.member(cfg, key):
        n = 1
        while config.member(cfg, "manager-{}".format(n) if n > 1 else "manager"):
            n += 1
        key = "manager-{}".format(n) if n > 1 else "manager"
    rid = team.manager_role(cfg)
    tpl = roles.by_id(rid, packs.of(cfg)["id"])
    m = {"name": key, "display": display, "role": rid,
         "role_title": tpl["title"] if tpl else "Manager",
         "focus": "running the {} for the {}".format(packs.of(cfg)["unit"], boss),
         "agent": "claude", "cmd": "claude"}
    cfg["members"].append(m)
    cfg["manager"] = key
    print("  ✓ {} is your manager".format(display))
    return m


def first_run():
    import os
    print(BANNER)
    if config.PROFILE != "default":
        print("Setting up profile '{}' — its own team in {}\n".format(config.PROFILE, config.STATE))
    ids = [p["id"] for p in packs.PACKS]
    hint = os.environ.get("MYTEAM_PRESET_HINT")
    j = choose("What kind of team is this? (sets the roles and skills on offer; "
               "you can change it later in setup)",
               ["{} — {}".format(p["en"], p["blurb"]) for p in packs.PACKS],
               default=ids.index(hint) + 1 if hint in ids else 1)
    pack = packs.PACKS[j]
    group = ask("What's it called? (e.g. {})".format(pack["example"]), "My Team")
    cfg = dict(config.DEFAULTS)
    cfg["group"] = group
    cfg["pack"] = pack["id"]
    cfg["members"] = []
    make_manager(cfg)
    from . import team
    others = [c for c in team.installed_clis() if c != "claude"]
    if others:
        yn = ask("{} found — may the manager use it for some jobs? (y/n)".format(
            " and ".join(team.CLIS[c]["label"] for c in others)), "y")
        cfg.setdefault("prefs", {})["other_clis"] = yn.lower().startswith("y")
    print("\nSpecialists (bookkeeper, writer, researcher ...) don't need names — your")
    print("manager adds and wakes them as jobs need. You can also add some now.")
    while ask("add a specialist now? (y/n)", "n").lower().startswith("y"):
        hire(cfg)
    config.save(cfg)
    config.shared_dirs()
    from . import skills
    skills.sync(cfg)
    _seed_handbook(cfg)
    print("\n✓ {} is founded — manager {}, {} specialist(s); config in {}".format(
        group, config.display(cfg["members"][0]), len(cfg["members"]) - 1, config.CONFIG))
    print("✓ shared skills + role instructions rendered for every member")
    print("\nNext:  myteam up   (start your manager)   then   myteam   (talk to them)")
    return cfg


def _seed_handbook(cfg):
    hb = config.STATE / "handbook"
    hb.mkdir(parents=True, exist_ok=True)
    readme = hb / "README.md"
    if not readme.exists():
        readme.write_text(packs.handbook_readme(cfg))
