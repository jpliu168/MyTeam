"""tmux-backed persistent member sessions (same engine as ASCEND2)."""
import os
import shlex
import shutil
import subprocess
import time

from . import config

PREFIX = "myteam-"
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
        subprocess.run(["tmux", "new-session", "-d", "-s", name, "-c", cwd,
                        prefix + " " + cmd], check=True)
    if attach:
        attach_to(name)
    return name


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
        subprocess.run(["tmux", "new-session", "-d", "-s", DAEMON, cmd], check=True)
        return True
    return False
