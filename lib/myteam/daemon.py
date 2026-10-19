"""myteamd — the minimal team daemon (the mailman + status watcher).

Runs inside its own tmux session (`myteam daemon start`). Every POLL seconds:
delivers queued bus messages to members that have gone idle, and logs status
changes to ~/.myteam/daemon.log. Deliberately tiny; schedules and nudges can
grow here later.
"""
import json
import time

from . import bus, config, sessions

WEEKLY = ("[myteam weekly] Time for the weekly tidy: (1) merge/prune "
          "handbook/preferences.md, specialists' NOTEBOOK.md files and ~/myteam/skills so "
          "they stay short and correct; (2) put 'What we learned this week' (`myteam "
          "learned`) and anything stuck in your next summary to the boss; (3) sleep idle "
          "specialists.")


def weekly_nudge(now=None):
    """Monday from 8am: once per ISO week, nudge the manager (queued if asleep)."""
    from . import team
    now = now or time.localtime()
    if now.tm_wday != 0 or now.tm_hour < 8:
        return False
    st_path = config.STATE / "daemon-state.json"
    try:
        st = json.loads(st_path.read_text())
    except (OSError, ValueError):
        st = {}
    week = time.strftime("%G-W%V", now)
    if st.get("weekly") == week:
        return False
    cfg = config.load()
    mg = team.manager(cfg) if cfg else None
    if not mg:
        return False
    bus.deliver(sessions.sname(mg["name"]), WEEKLY, sender="owner", kind="weekly")
    st["weekly"] = week
    st_path.write_text(json.dumps(st))
    _log("weekly tidy nudge -> {}".format(mg["name"]))
    return True

POLL = 15


def _log(msg):
    with open(config.STATE / "daemon.log", "a") as f:
        f.write("{} {}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), msg))


def run():
    _log("daemon started")
    print("myteamd running — mailman + status watcher (ctrl-c to stop)")
    last = {}
    while True:
        try:
            for name in sessions.list_sessions():
                st = bus.current_status(name)
                if last.get(name) not in (None, st):
                    _log("{}: {} -> {}".format(name, last[name], st))
                last[name] = st
                n = bus.flush(name)
                if n:
                    _log("delivered {} queued message(s) to {}".format(n, name))
                    print("mailman: {} message(s) -> {}".format(n, name))
            weekly_nudge()
        except Exception as e:  # keep the daemon alive, always
            _log("error: {!r}".format(e))
        time.sleep(POLL)
