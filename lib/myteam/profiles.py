"""Profiles: several independent teams on one computer, e.g. "research-pi"
(a lab run for a PI) and "research-admin" (a research office run for a
director). Each profile is a whole team — its own state folder, manager,
specialists, handbook, deliverables, database and tmux sessions — so two
profiles can run side by side without seeing each other.

    myteam list                     every profile; * = the active one
    myteam use research-admin       switch (creates it if new, then sets it up)
    myteam -p research-pi inbox     one command against another profile

Where things live (all under ~/myteam, visible in Finder):
    default profile   ~/myteam/                      (the original team, unchanged)
    other profiles    ~/myteam/profiles/<name>/      (each a whole team)
    registry          ~/myteam/profiles.json         (which one is active)

Which profile a command uses, first match wins:
    MYTEAM_PROFILE  (set by -p/--profile, and inside every member session)
    MYTEAM_STATE    (old-style explicit folder)
    MYTEAM_SESSION  (a member started before profiles existed: from its tmux name)
    the registry's active profile, else "default".

This module must not import config (config imports it).
"""
import json
import os
import re
from pathlib import Path

DEFAULT = "default"
HOME = Path.home()
ROOT = HOME / "myteam"                      # default team; other profiles inside it
PROFILES_DIR = ROOT / "profiles"
REGISTRY = Path(os.environ.get("MYTEAM_PROFILES", str(ROOT / "profiles.json")))

# Guess a field preset from a profile name (used when a new profile is set up).
_HINTS = [
    ("graduate", ("grad", "graduate", "phd", "student", "thesis", "dissertation", "masters", "ms")),
    ("academic-admin", ("academic", "dean", "chair", "head", "dept", "department", "college", "provost")),
    ("research-admin", ("admin", "office", "ord", "development", "sponsored", "srs", "vcr")),
    ("research", ("pi", "lab", "research", "science")),
    ("teaching", ("course", "teach", "class", "mea")),
    ("nonprofit", ("nonprofit", "club", "charity", "community")),
    ("freelance", ("freelance", "studio", "creator", "consult")),
    ("business", ("business", "company", "shop", "llc", "inc")),
]


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")
    return s[:32].strip("-")


def preset_hint(name):
    words = set(slug(name).split("-"))
    for pid, keys in _HINTS:
        if words & set(keys):
            return pid
    return None


def load():
    try:
        reg = json.loads(REGISTRY.read_text())
    except (OSError, ValueError):
        reg = {}
    reg.setdefault("active", DEFAULT)
    reg.setdefault("profiles", {})
    reg["profiles"].setdefault(DEFAULT, {"state": str(ROOT)})
    return reg


def save(reg):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, indent=2) + "\n")
    tmp.replace(REGISTRY)


def state_for(name, reg=None):
    reg = reg or load()
    p = reg["profiles"].get(name)
    if p and p.get("state"):
        return Path(os.path.expanduser(p["state"]))
    return ROOT if name == DEFAULT else PROFILES_DIR / name


def prefix(name):
    """tmux session prefix. The default keeps the original 'myteam-' so teams
    already running are untouched; other profiles get 'myteam_<name>-', which
    never starts with 'myteam-', so profiles never see each other's sessions."""
    return "myteam-" if name == DEFAULT else "myteam_{}-".format(name)


def _from_session(sess, reg):
    sess = sess or ""
    if sess.startswith("myteam_"):
        known = sorted(reg["profiles"], key=len, reverse=True)   # longest name first
        hit = next((n for n in known if sess.startswith(prefix(n))), None)
        if hit:
            return hit
        m = re.match(r"^myteam_([a-z0-9-]+?)-", sess)
        return m.group(1) if m else None
    return DEFAULT if sess.startswith("myteam-") else None


def resolve():
    """(profile name, state folder) for this process."""
    env = os.environ
    reg = load()
    if env.get("MYTEAM_PROFILE"):
        name = slug(env["MYTEAM_PROFILE"]) or DEFAULT
        state = Path(env["MYTEAM_STATE"]) if env.get("MYTEAM_STATE") else state_for(name, reg)
        return name, state
    if env.get("MYTEAM_STATE"):
        st = Path(env["MYTEAM_STATE"]).expanduser()
        for n, p in reg["profiles"].items():
            if state_for(n, reg) == st:
                return n, st
        return DEFAULT, st
    from_sess = _from_session(env.get("MYTEAM_SESSION"), reg)
    if from_sess:
        return from_sess, state_for(from_sess, reg)
    name = reg.get("active") or DEFAULT
    return name, state_for(name, reg)


CURRENT, STATE = resolve()


def register(name, state):
    """Remember a profile once it has a team (called by config.save)."""
    reg = load()
    p = reg["profiles"].setdefault(name, {})
    if p.get("state") != str(state):
        p["state"] = str(state)
        save(reg)


def use(name):
    """Make <name> the active profile. Returns (name, state, is_new)."""
    name = slug(name)
    if not name:
        raise SystemExit("give the profile a name, e.g. `myteam use research-admin`")
    reg = load()
    state = state_for(name, reg)
    is_new = not (state / "config.json").exists()
    reg["profiles"].setdefault(name, {})["state"] = str(state)
    reg["active"] = name
    save(reg)
    return name, state, is_new


def all_profiles():
    """[(name, state, cfg or None)] — registered ones plus any team found in
    ~/myteam/profiles/."""
    reg = load()
    names = dict((n, state_for(n, reg)) for n in reg["profiles"])
    if PROFILES_DIR.is_dir():
        for d in sorted(PROFILES_DIR.iterdir()):
            if (d / "config.json").exists():
                n = slug(d.name)
                if n and n not in names:
                    names[n] = d
    out = []
    for n, st in names.items():
        try:
            cfg = json.loads((st / "config.json").read_text())
        except (OSError, ValueError):
            cfg = None
        out.append((n, st, cfg))
    out.sort(key=lambda r: (r[0] != DEFAULT, r[0]))
    return out


def apply_argv(argv):
    """Strip a leading -p/--profile NAME from argv and pin this process (and
    everything it starts) to that profile. Called by bin/ before importing."""
    args = list(argv)
    if args and (args[0] in ("-p", "--profile") and len(args) > 1):
        name, args = args[1], args[2:]
    elif args and args[0].startswith("--profile="):
        name, args = args[0].split("=", 1)[1], args[1:]
    else:
        return args
    os.environ["MYTEAM_PROFILE"] = slug(name) or DEFAULT
    os.environ.pop("MYTEAM_STATE", None)
    global CURRENT, STATE
    CURRENT, STATE = resolve()
    return args


def short_path(p):
    p = str(p)
    h = str(HOME)
    return "~" + p[len(h):] if p.startswith(h) else p
