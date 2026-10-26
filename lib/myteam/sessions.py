"""tmux-backed persistent member sessions (same engine as ASCEND2)."""
import os
import shlex
import shutil
import subprocess
import time

from . import config, profiles

PREFIX = profiles.prefix(config.PROFILE)   # "myteam-" for the default profile
DAEMON = PREFIX + "daemon"


def tmux_ok():
    return shutil.which("tmux") is not None


def sname(member_name):
    return PREFIX + member_name


def list_sessions(include_daemon=False):
    if not tmux_ok():
        return []
    r = subprocess.run(["tmux", "ls", "-F", "#{session_name}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = [l for l in r.stdout.splitlines() if l.startswith(PREFIX)]
    if not include_daemon:
        out = [l for l in out if l != DAEMON]
    return out


def resolve(token, sessions=None):
    sessions = list_sessions() if sessions is None else sessions
    full = token if token.startswith(PREFIX) else PREFIX + token
    if full in sessions:
        return full
    hits = [s for s in sessions if token in s]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit("no running member matches '{}' (myteam ls)".format(token))
    raise SystemExit("'{}' is ambiguous: {}".format(token, ", ".join(hits)))


def launch(cfg, m, attach=True, cli=None):
    name = sname(m["name"])
    cwd = str(config.member_dir(m["name"]))
    envs = {"MYTEAM_MEMBER": m["name"], "MYTEAM_SESSION": name,
            "MYTEAM_ROLE": m["role"], "MYTEAM_GROUP": cfg["group"],
            "MYTEAM_WORKDIR": cwd,
            "MYTEAM_PROFILE": config.PROFILE, "MYTEAM_STATE": str(config.STATE),
            "MYTEAM_FOLDERS": os.pathsep.join(config.access_dirs(m))}
    from . import team
    if cli is None:
        cli, _ = team.pick_cli(cfg, m)
    cmd = team.build_cmd(cfg, m, cli)        # folder flags + auto-edit mode per CLI
    envs["MYTEAM_CLI"] = cli
    if not tmux_ok():
        print("tmux not found — running without persistence (`brew install tmux`).")
        env = os.environ.copy()
        env.update(envs)
        subprocess.run(cmd, shell=True, cwd=cwd, env=env)
        return name
    if name not in list_sessions():
        prefix = " ".join("{}={}".format(k, shlex.quote(v)) for k, v in envs.items())
        # If the agent quits, save its last screen so "exited right after
        # starting" can say why (members/<name>/last-exit.log).
        log = shlex.quote(str(config.member_dir(m["name"]) / "last-exit.log"))
        after = ("; rc=$?; tmux capture-pane -p -J -t {n} -S -200 > {log} 2>/dev/null; "
                 "echo \"[exited with code $rc at $(date)]\" >> {log}").format(
                     n=shlex.quote(name), log=log)
        try:
            os.remove(str(config.member_dir(m["name"]) / "last-exit.log"))
        except OSError:
            pass
        subprocess.run(["tmux", "new-session", "-d", "-s", name, "-c", cwd,
                        "export " + prefix + "; (" + cmd + ")" + after], check=True)
    if attach:
        attach_to(name)
    return name


def last_exit(member_name, lines=6):
    """The last lines a member's agent printed before it quit ('' if none)."""
    f = config.member_dir(member_name) / "last-exit.log"
    try:
        out = [l.rstrip() for l in f.read_text(errors="replace").splitlines() if l.strip()]
    except OSError:
        return ""
    return "\n".join(out[-lines:])


def attach_to(name):
    if os.environ.get("TMUX"):
        subprocess.run(["tmux", "switch-client", "-t", name])
    else:
        subprocess.run(["tmux", "attach-session", "-t", name])


def tail(name, lines=30):
    r = subprocess.run(["tmux", "capture-pane", "-p", "-t", name],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = [l.rstrip() for l in r.stdout.splitlines()]
    while out and not out[-1]:
        out.pop()
    return out[-lines:]


def history(name, lines=3000):
    """Visible screen PLUS scrollback, wrapped lines re-joined (-J). Used to
    pull a member's whole reply, not just what fits on the screen."""
    r = subprocess.run(["tmux", "capture-pane", "-p", "-J", "-t", name, "-S", "-{}".format(lines)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = [l.rstrip() for l in r.stdout.splitlines()]
    while out and not out[-1]:
        out.pop()
    return out


def _claude_transcript(member_name):
    """Newest Claude Code transcript for this member's working folder
    (~/.claude/projects/<folder with non-alphanumerics as '-'>/<id>.jsonl)."""
    import re
    from pathlib import Path
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "projects"
    cwd = str(config.member_dir(member_name).resolve())
    d = base / re.sub(r"[^A-Za-z0-9]", "-", cwd)
    try:
        files = sorted(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
    except OSError:
        return None
    return files[-1] if files else None


def _texts(content):
    if isinstance(content, str):
        return [content]
    return [b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"]


def claude_reply(member_name, since=0):
    """The full text of the member's last answer, read from Claude Code's own
    transcript — complete, however long, and without screen clutter.
    Returns a list of lines, or None if there is no usable transcript."""
    import json
    f = _claude_transcript(member_name)
    try:
        if not f or f.stat().st_mtime < since - 5:
            return None
        size = f.stat().st_size
        with open(f, "rb") as fh:
            fh.seek(max(0, size - 4_000_000))
            raw = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    ents = []
    for l in raw:
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if e.get("type") in ("user", "assistant") and isinstance(e.get("message"), dict) \
                and not e.get("isSidechain"):
            ents.append(e)
    # the last prompt MyTeam typed in ("[myteam msg from owner] ...")
    start = None
    for i in range(len(ents) - 1, -1, -1):
        e = ents[i]
        if e["type"] == "user" and any("[myteam " in t for t in _texts(e["message"].get("content"))):
            start = i
            break
    if start is None:
        return None
    after = ents[start + 1:]
    # the final answer = assistant text after the last tool result; else all text
    last_tool = max((i for i, e in enumerate(after) if e["type"] == "user"), default=-1)
    final = [t for e in after[last_tool + 1:] if e["type"] == "assistant"
             for t in _texts(e["message"].get("content")) if t.strip()]
    if not final:
        final = [t for e in after if e["type"] == "assistant"
                 for t in _texts(e["message"].get("content")) if t.strip()]
    if not final:
        return None
    return "\n\n".join(final).strip().splitlines()


def reply_of(name, keep=400, since=0):
    """The member's latest reply. Claude Code: read from its transcript (full
    text). Other CLIs: everything after the last message MyTeam typed into the
    terminal (screen + scrollback), minus the CLI's chrome."""
    from . import status
    member = name[len(PREFIX):] if name.startswith(PREFIX) else name
    full = claude_reply(member, since)
    if full:
        return full
    return status.clean_reply(history(name), keep=keep)


def send_text(name, text):
    """Paste text + Enter into a session. Returns False if the session is gone."""
    r1 = subprocess.run(["tmux", "send-keys", "-t", name, "-l", text],
                        capture_output=True)
    time.sleep(0.3)
    r2 = subprocess.run(["tmux", "send-keys", "-t", name, "Enter"],
                        capture_output=True)
    return r1.returncode == 0 and r2.returncode == 0


def send_keys(name, *keys):
    """Press keys (tmux names, e.g. "Enter", "Down") in a session."""
    subprocess.run(["tmux", "send-keys", "-t", name] + list(keys), capture_output=True)


def kill(name):
    subprocess.run(["tmux", "kill-session", "-t", name])


OFFICE = PREFIX + "office"


def build_office():
    """One session, one tab (window) per running member — the whole team in
    a single terminal. Rebuilt fresh on every call."""
    import subprocess as sp
    members = list_sessions()
    if not members:
        raise SystemExit("no members running — `myteam up` first")
    sp.run(["tmux", "kill-session", "-t", OFFICE], capture_output=True)
    sp.run(["tmux", "new-session", "-d", "-s", OFFICE, "-n", "team",
            "bash -lc 'echo \"{} office — ctrl-b n/p or ctrl-b <number> to switch tabs; ctrl-b d to leave\"; exec bash'".format(config.load()["group"].replace("'", ""))],
           check=True)
    for m in members:
        sp.run(["tmux", "link-window", "-s", m + ":", "-t", OFFICE + ":"],
               capture_output=True)
        sp.run(["tmux", "rename-window", "-t", m + ":", m[len(PREFIX):]],
               capture_output=True)
    sp.run(["tmux", "select-window", "-t", OFFICE + ":1"], capture_output=True)
    return OFFICE


def run_daemon_session(cmd):
    if not tmux_ok():
        raise SystemExit("the daemon needs tmux (`brew install tmux`)")
    if DAEMON not in list_sessions(include_daemon=True):
        pin = "MYTEAM_PROFILE={} MYTEAM_STATE={} ".format(
            shlex.quote(config.PROFILE), shlex.quote(str(config.STATE)))
        subprocess.run(["tmux", "new-session", "-d", "-s", DAEMON, pin + cmd], check=True)
        return True
    return False
