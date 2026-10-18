"""First-run onboarding ("found your team") and the hiring mini-wizard."""
import re
import shutil

from . import config, packs, roles

BANNER = r"""
  __  __       _____
 |  \/  |_   _|_   _|__  __ _ _ __ ___    your team · your agents
 | |\/| | | | || |/ _ \/ _` | '_ ` _ \    one owner · many roles
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
    """Add one member interactively. Returns the member dict or None."""
    print("\n-- Hire a member --")
    display = ask("member's name (e.g. Sam)")
    name = _slug(display)
    if not name:
        return None
    if config.member(cfg, name):
        print("  '{}' already exists — use `myteam edit {}`".format(name, name))
        return None
    lib = roles.for_pack(packs.of(cfg)["id"])
    i = choose("role?", roles.menu(packs.of(cfg)["id"]))
    if i < len(lib):
        tpl = lib[i]
        role, role_title = tpl["id"], tpl["title"]
        custom_instructions = ""
    else:
        role = _slug(ask("custom role id (e.g. field-work)"))
        role_title = ask("one-line role title")
        custom_instructions = ask("describe the role's duties (one paragraph)")
    focus = ask("area of focus for {} (one sentence, or blank)".format(name), "")
    j = choose("which agent CLI runs this member?",
               ["{}{}".format(label, "  (installed ✓)" if shutil.which(cid) else "")
                if cid != "custom" else label
                for cid, label in AGENT_CLIS])
    cid = AGENT_CLIS[j][0]
    cmd = cid if cid != "custom" else ask("command to launch it (e.g. `gemini`)")
    if not cmd:
        print("  no command given — member not hired")
        return None
    m = {"name": name, "display": display.strip() or name, "role": role,
         "role_title": role_title, "focus": focus, "agent": cid, "cmd": cmd}
    if custom_instructions:
        m["instructions"] = custom_instructions
    folders = ask_folders(m)
    if folders:
        m["folders"] = folders
    if cid == "custom" and folders:
        print("  note: a custom CLI isn't given folder flags — it gets $MYTEAM_FOLDERS"
              " and the list in its AGENTS.md")
    cfg["members"].append(m)
    print("  ✓ hired {} ({}) — working folder {}".format(
        m["display"], role, config.member_dir(name)))
    return m


def first_run():
    print(BANNER)
    j = choose("What kind of team is this? (sets the roles and skills on offer; "
               "you can change it later in setup)",
               ["{} — {}".format(p["en"], p["blurb"]) for p in packs.PACKS])
    pack = packs.PACKS[j]
    group = ask("What's it called? (e.g. {})".format(pack["example"]), "My Team")
    cfg = dict(config.DEFAULTS)
    cfg["group"] = group
    cfg["pack"] = pack["id"]
    cfg["members"] = []
    print("\nNow hire your team — as many members as you want; you can always")
    print("`myteam hire`, `myteam edit` or `myteam retire` later.")
    while True:
        hire(cfg)
        if not ask("hire another member? (y/n)", "y" if not cfg["members"] else "n"
                   ).lower().startswith("y"):
            break
    config.save(cfg)
    config.shared_dirs()
    from . import skills
    skills.sync(cfg)
    _seed_handbook(cfg)
    print("\n✓ {} is founded: {} member(s), config in {}".format(
        group, len(cfg["members"]), config.CONFIG))
    print("✓ shared skills + role instructions rendered for every member")
    print("\nNext:  myteam roster   |  myteam start <member>  |  myteam assign <member> \"task\"")
    return cfg


def _seed_handbook(cfg):
    hb = config.STATE / "handbook"
    hb.mkdir(parents=True, exist_ok=True)
    readme = hb / "README.md"
    if not readme.exists():
        readme.write_text(packs.handbook_readme(cfg))
