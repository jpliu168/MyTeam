"""myteamd — the minimal team daemon (the mailman + status watcher).

Runs inside its own tmux session (`myteam daemon start`). Every POLL seconds:
delivers queued bus messages to members that have gone idle, and logs status
changes to ~/.myteam/daemon.log. Deliberately tiny; schedules and nudges can
grow here later.
"""
import time

from . import bus, config, sessions

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
        except Exception as e:  # keep the daemon alive, always
            _log("error: {!r}".format(e))
        time.sleep(POLL)
