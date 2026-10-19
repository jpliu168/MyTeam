"""MyTeam config & state. Everything lives under ~/myteam/ (override: MYTEAM_STATE).

A visible folder, deliberately: the owner browses deliverables/ and handbook/ in
Finder. (_migrate is inherited from MyLab; harmless — there is no old hidden ~/.myteam.)
"""
import json
import os
import re
import shutil
from pathlib import Path

STATE = Path(os.environ.get("MYTEAM_STATE", str(Path.home() / "myteam")))
CONFIG = STATE / "config.json"

_OLD_STATE = Path.home() / ".myteam"


def _migrate():
    """One-time move of a pre-v0.1.1 hidden ~/.myteam to the visible location."""
    if "MYTEAM_STATE" in os.environ:
        return
    if _OLD_STATE.is_dir() and (_OLD_STATE / "config.json").exists() \
            and not CONFIG.exists():
        if STATE.exists() and any(STATE.iterdir()):
            print("note: both {} and {} exist — using the new one; merge the old "
                  "by hand".format(_OLD_STATE, STATE))
            return
        if STATE.exists():
            STATE.rmdir()
        shutil.move(str(_OLD_STATE), str(STATE))
        print("✓ moved your team from {} to {} (now visible in Finder)".format(
            _OLD_STATE, STATE))
        try:  # re-render skills so member workspaces point at the new paths
            cfg = json.loads(CONFIG.read_text())
            from . import skills
            skills.sync(cfg)
            print("✓ re-rendered member skills for the new location")
        except Exception as e:
            print("  (run `myteam skills sync` once — auto re-render failed: {})".format(e))

DEFAULTS = {
    "group": "My Team",
    # members: {name, role, focus, agent (claude|codex|custom), cmd,
    #           folders: [extra absolute paths the member may read/write]}
    "members": [],
}


def load():
    _migrate()
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text())
        for k, v in DEFAULTS.items():
            cfg.setdefault(k, v)
        return cfg
    return None


def save(cfg):
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n")
    tmp.replace(CONFIG)


def member(cfg, name):
    return next((m for m in cfg["members"] if m["name"] == name), None)


def display(m):
    """What the owner sees and types; falls back to the internal key."""
    return m.get("display") or m["name"]


def member_dir(name):
    d = STATE / "members" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# Shared team folders every member may read/write besides its own working folder.
SHARED_ACCESS = ("deliverables", "handbook", "bus")
# (plus ~/myteam/skills — the team's learned skills; see access_dirs)


def parse_folders(text):
    """'~/a, ~/b' or one-per-line -> (absolute paths, problems). '-' clears."""
    if isinstance(text, (list, tuple)):
        items = list(text)
    else:
        text = (text or "").strip()
        if text == "-":
            return [], []
        items = re.split(r"[,\n]", text)
    out, bad = [], []
    for raw in items:
        raw = str(raw).strip().strip('"').strip("'")
        if not raw:
            continue
        path = Path(os.path.expandvars(raw)).expanduser()
        if not path.is_absolute():
            bad.append("{} (use a full path, e.g. ~/Clients/Acme)".format(raw))
            continue
        path = path.resolve()
        if not path.is_dir():
            bad.append("{} (folder not found)".format(raw))
            continue
        if str(path) not in out:
            out.append(str(path))
    return out, bad


def member_folders(m):
    """Extra folders the owner granted this member (absolute paths)."""
    return [f for f in m.get("folders") or [] if f]


def access_dirs(m):
    """Everything besides the working folder this member's agent may use."""
    shared = [str(d) for k, d in shared_dirs().items() if k in SHARED_ACCESS]
    shared.append(str(STATE / "skills"))      # team-learned skills (everyone may improve them)
    return shared + [f for f in member_folders(m) if f not in shared]


def shared_dirs():
    out = {}
    for sub in ("deliverables", "handbook", "bus", "alumni", "skills"):
        d = STATE / sub
        d.mkdir(parents=True, exist_ok=True)
        out[sub] = d
    return out


def root():
    """MyTeam install root (folder holding bin/, lib/, skills/)."""
    return Path(__file__).resolve().parents[2]
