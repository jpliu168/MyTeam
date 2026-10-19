"""Control room v2 — a full-screen terminal UI (curses, stdlib only).

Layout:
  ┌ title bar: group name · clock ──────────────────────────────┐
  │ MEMBERS (live)      │  feed: your orders, deliveries,       │
  │  ● sam    chief     │  agent↔agent traffic, replies,        │
  │  ◐ david  slides    │  system notes                         │
  │  ○ lucy   outreach  │                                       │
  ├─────────────────────┴───────────────────────────────────────┤
  │ you> input line (Tab completes, ↑↓ history, PgUp/Dn scroll)  │
  └ hint bar ───────────────────────────────────────────────────┘

No LLM here — plain switchboard, same commands as the plain REPL
(`myteam plain`). Falls back automatically if the terminal can't do curses.
"""
import curses
import json
import textwrap
import time

import unicodedata

from . import board, brief, bus, config, roles, sessions, status


def cols(s):
    """Display width: CJK characters take two terminal columns."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def fit(s, n):
    """Cut s to at most n display columns (adds … when cut)."""
    if n <= 0:
        return ""
    if cols(s) <= n:
        return s
    out, used = "", 0
    for c in s:
        cw = cols(c)
        if used + cw > n - 1:
            break
        out += c
        used += cw
    return out + "…"

POLL = 1.5

# ---- interface languages -------------------------------------------------
S = {
    "en": {
        "room": "control room",
        "members": "MEMBERS",
        "manager_hdr": "MANAGER",
        "spec_hdr": "SPECIALISTS",
        "asleep": "asleep",
        "needs_you": "needs you",
        "shortcuts": "SHORTCUTS",
        "sc_lines": [
            "just type      talk to {mgr}",
            "inbox          what needs you",
            "approve <id>   say yes",
            "staff          the team",
            "@writer <msg>  a specialist",
            "open <m>       visit a terminal",
            "ctrl-b then d  come back",
            "setup / set    manage team",
            "help / h       all commands",
            "quit / q       leave",
        ],
        "queued": "queued msgs",
        "opentasks": "open tasks ",
        "hint": " Tab complete · ↑↓ history · PgUp/Dn scroll · setup · help · quit · watch {} ",
        "welcome": ("Welcome to the {} control room. Just type — it goes to your "
                    "manager, {mgr}. `inbox` = what needs you · `help` = all commands."),
        "notunderstood": "not understood — try `help`",
        "back": "(back in the control room)",
        "tip": ("{mgr} brings in specialists when a job needs them and puts them to "
                "sleep after — you don't need to start anyone."),
        "left": "left the control room — the team keeps working.",
        "help": [
            "talk      just type — it goes to your manager",
            "you       inbox = what needs you · approve <id> · decline <id> [reason]",
            "team      staff = manager, specialists, role catalog · learned = what the team learned",
            "direct    writer: <msg> · @writer <msg> · @all <msg>  (talk to a specialist yourself)",
            "board     assign <m> <task> · tasks · done <id>",
            "views     roster · standup · log · watch on|off (agent-to-agent traffic)",
            "briefing  brief = full briefing in the feed · brief on|off = pinned panel up top",
            "run       up = start the manager · start <m> = start one · open <m> = start+enter",
            "visit     open <m> = step into their terminal · RETURN: press ctrl-b, then d",
            "setup     hire/edit/retire members, change their agent CLI, language, skills",
            "keys      Tab complete · up/down history · PgUp/PgDn scroll feed",
            "leave     quit  (members keep working in the background)",
            "'delivered' = typed into their terminal; the reply prints here when they finish.",
            "'queued' = they were busy/blocked; the mailman hands it over when they go idle.",
        ],
        "setup_menu": [
            "— {} setup —  (plain mode; the control room resumes when you finish)",
            "  1) add a specialist",
            "  2) edit a member (role, focus, agent CLI: claude/codex/other)",
            "  3) retire a member (archive to alumni/)",
            "  4) language / 语言  (current: {})",
            "  5) re-render shared skills for everyone",
            "  6) profile (who you are — company, lab, course … — every member reads it)",
            "  7) field preset (business / research lab / teaching / nonprofit / freelance)",
            "  0) back to the control room",
        ],
        "setup_which": "which member",
        "setup_lang": "interface language: 1) English  2) 中文",
        "setup_done": "setup closed — back to the control room.",
        "brief": "BRIEFING — what the team is doing",
        "brief_off": "asleep",
        "brief_none": "(no one is running — `up` starts your manager)",
    },
    "zh": {
        "room": "控制室",
        "members": "成员",
        "manager_hdr": "经理",
        "spec_hdr": "专家",
        "asleep": "休眠",
        "needs_you": "待你决定",
        "shortcuts": "快捷操作",
        "sc_lines": [
            "直接输入       与 {mgr} 对话",
            "inbox          待你处理的事",
            "approve <编号> 批准",
            "staff          团队一览",
            "@专家 <消息>   直接找专家",
            "open <成员>    进入其终端",
            "ctrl-b 再按 d  返回这里",
            "setup / set    团队设置",
            "help / h       全部命令",
            "quit / q       退出",
        ],
        "queued": "待送消息",
        "opentasks": "未完任务",
        "hint": " Tab 补全 · ↑↓ 历史 · PgUp/Dn 翻页 · setup 设置 · help 帮助 · quit 退出 · watch {} ",
        "welcome": "欢迎来到 {} 控制室。直接输入即可与经理 {mgr} 对话；`inbox` 查看待你处理的事；`help` 查看全部命令。",
        "notunderstood": "没看懂 — 试试 `help`",
        "back": "（已返回控制室）",
        "tip": "{mgr} 会按需唤醒专家、完成后让其休眠 — 你不需要启动任何人。",
        "left": "已离开控制室 — 团队在后台继续运行。",
        "help": [
            "对话      直接输入 — 发给你的经理",
            "你        inbox 待你处理 · approve <编号> 批准 · decline <编号> [理由] 拒绝",
            "团队      staff 经理/专家/角色目录 · learned 团队最近学到了什么",
            "直接      writer: <消息> · @writer <消息> · @all <消息>（自己直接找专家）",
            "任务板    assign <成员> <任务> · tasks 查看 · done <编号> 完成",
            "查看      roster 名册 · standup 晨会 · log 通信记录 · watch on|off（成员间通信直播）",
            "简报      brief = 在信息流中显示完整简报 · brief on|off = 顶部简报面板开/关",
            "启动      up = 启动经理 · start <成员> = 启动某位 · open <成员> = 启动并进入",
            "探访      open <成员> = 进入其终端 · 返回：先按 ctrl-b，再按 d",
            "设置      setup：聘用/编辑/退休成员、更换其 agent CLI、语言、技能",
            "按键      Tab 补全 · ↑↓ 历史 · PgUp/PgDn 翻页",
            "离开      quit（成员在后台继续工作）",
            "'delivered' = 已送入其终端；对方完成后回复会显示在这里。",
            "'queued' = 对方正忙或被阻塞；空闲时邮差会自动送达。",
        ],
        "setup_menu": [
            "— {} 设置 —（普通模式；完成后自动回到控制室）",
            "  1) 添加专家",
            "  2) 编辑成员（角色、方向、agent CLI：claude/codex/其他）",
            "  3) 成员退休（归档到 alumni/）",
            "  4) 语言 / language（当前：{}）",
            "  5) 为所有成员重新生成共享技能",
            "  6) 简介（公司、实验室、课程等 — 每位成员都会读）",
            "  7) 领域预设（企业 / 科研实验室 / 教学 / 非营利 / 自由职业）",
            "  0) 返回控制室",
        ],
        "setup_which": "哪位成员",
        "setup_lang": "界面语言: 1) English  2) 中文",
        "setup_done": "设置完成 — 返回控制室。",
        "brief": "简报 — 团队在做什么",
        "brief_off": "休眠",
        "brief_none": "（没有成员在运行 — 用 `up` 启动经理）",
    },
}


def lang_of(cfg):
    return cfg.get("prefs", {}).get("lang", "en")


ROLE_ZH = roles.ZH
STATUS_ZH = {"working": "工作中", "blocked": "待处理", "idle": "空闲",
             "off": "未运行", "gone": "已退出"}

C_TITLE, C_OK, C_WORK, C_BLOCK, C_DIM, C_PI, C_TRAFFIC, C_REPLY = range(1, 9)


class Room:
    def __init__(self, stdscr, cfg):
        self.scr = stdscr
        self.cfg = cfg
        self.feed = []            # list of (color, text, gid) — gid marks UI text
        self._gid = 0             # that is re-translated when the language changes
        self.scroll = 0           # lines from bottom
        self.input = ""
        self.history = []
        self.hist_i = None
        self.watch_traffic = True
        self.awaiting = {}
        self.statuses = {}
        self._offsets = {}
        self._last_poll = 0
        self.brief_on = True
        self.briefs = []
        self._last_brief = 0
        self.lang = lang_of(cfg)
        self.S = S.get(self.lang, S["en"])
        self._prime_offsets()

    # ---------- data ----------
    def _prime_offsets(self):
        d = config.STATE / "bus"
        if d.exists():
            for f in d.glob("*.log.jsonl"):
                self._offsets[f] = f.stat().st_size

    def short(self, s):
        return s[len(sessions.PREFIX):] if s.startswith(sessions.PREFIX) else s

    def _ui_text(self, key):
        """Interface text for a key like 'welcome' or 'help:3', current language."""
        if key.startswith("help:"):
            lines = self.S["help"]
            i = int(key[5:])
            return lines[i] if i < len(lines) else ""
        txt = self.S.get(key, "")
        mgr = self._mgr_name()
        if key == "welcome":
            return txt.replace("{mgr}", mgr).format(self.cfg["group"])
        return txt.replace("{mgr}", mgr)

    def _mgr_name(self):
        from . import team
        mg = team.manager(self.cfg)
        return config.display(mg) if mg else ("经理" if self.lang == "zh" else "the manager")

    def say_ui(self, key, color=0):
        self._gid += 1
        self.say(self._ui_text(key), color, gid=(key, self._gid))

    def relocalize(self):
        """After a language switch, rewrite every piece of interface text
        already in the feed; members' words and traffic stay as they were."""
        old, self.feed, last = self.feed, [], None
        for entry in old:
            gid = entry[2] if len(entry) > 2 else None
            if gid is None:
                self.feed.append(entry)
            elif gid != last:
                self.say(self._ui_text(gid[0]), entry[0], gid=gid)
            last = gid

    def say(self, text, color=0, gid=None):
        for line in text.splitlines() or [""]:
            w = max(20, self.scr.getmaxyx()[1] - self._side_width(self.scr.getmaxyx()[1]) - 4)
            for part in textwrap.wrap(line, w) or [""]:
                while cols(part) > w:          # CJK text: split by columns
                    head = fit(part, w + 1)[:-1]
                    self.feed.append((color, head, gid))
                    part = part[len(head):]
                self.feed.append((color, part, gid))
        self.feed = self.feed[-2000:]

    def poll(self):
        if time.time() - self._last_poll < POLL:
            return
        self._last_poll = time.time()
        live = sessions.list_sessions()
        self.statuses = {}
        for m in self.cfg["members"]:
            name = sessions.sname(m["name"])
            if name in live:
                self.statuses[m["name"]] = status.classify(sessions.tail(name))
                bus.flush(name)
            else:
                self.statuses[m["name"]] = "off"
        if time.time() - self._last_brief > 4:
            self._last_brief = time.time()
            try:
                self.briefs = brief.collect(self.cfg, self.statuses, live)
            except Exception:
                self.briefs = []
        # traffic
        d = config.STATE / "bus"
        if d.exists():
            for f in sorted(d.glob("*.log.jsonl")):
                pos = self._offsets.get(f, 0)
                size = f.stat().st_size
                if size <= pos:
                    continue
                with open(f) as fh:
                    fh.seek(pos)
                    chunk = fh.read()
                self._offsets[f] = size
                for line in chunk.splitlines():
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    frm = rec.get("from", "")
                    mgs = self._mgr_session()
                    if mgs and rec.get("to") == mgs and rec.get("kind") in ("report", "decision"):
                        self.awaiting[mgs] = time.time()     # the manager will summarize
                    if frm.startswith(sessions.PREFIX) and self.watch_traffic:
                        t = rec.get("text", "")
                        self.say("⇄ {} → {} [{}] {}".format(
                            self.short(frm), self.short(rec.get("to", "?")),
                            rec.get("kind", "msg"),
                            t[:200] + ("…" if len(t) > 200 else "")), C_TRAFFIC)
        # replies
        for name, sent in list(self.awaiting.items()):
            if time.time() - sent < 6:
                continue
            st = bus.current_status(name)
            if st == "idle":
                del self.awaiting[name]
                self.say("── {} ──".format(self.short(name)), C_REPLY)
                for l in status.clean_reply(sessions.tail(name, 60)):
                    self.say("  " + l, 0)
                self.say("── end {0} · `open {0}` for the full screen ──".format(
                    self.short(name)), C_REPLY)
            elif st == "gone":
                del self.awaiting[name]
                self.say("✗ {} exited — `open {}` to investigate".format(
                    self.short(name), self.short(name)), C_BLOCK)

    def _mgr_session(self):
        from . import team
        mg = team.manager(self.cfg)
        return sessions.sname(mg["name"]) if mg else None

    # ---------- commands ----------
    def target(self, token):
        m = config.member(self.cfg, token)
        if m is None:
            tl = token.lower()
            exact = [x for x in self.cfg["members"]
                     if tl in (x["name"], config.display(x).lower())]
            hits = exact or [x for x in self.cfg["members"]
                             if tl in x["name"] or tl in config.display(x).lower()]
            m = hits[0] if len(hits) == 1 else None
        return m

    def send(self, member, text):
        name = sessions.sname(member["name"])
        if name not in sessions.list_sessions():
            from . import team
            self.say("(starting {} …)".format(config.display(member)), C_DIM)
            self.say("({})".format(team.wake(self.cfg, member, by="owner")), C_DIM)
        outcome = bus.deliver(name, text, sender="owner")
        self.awaiting[name] = time.time()
        self.say("you → {}: {}".format(config.display(member), text), C_PI)
        self.say("   {}".format(outcome), C_DIM)

    def handle(self, raw):
        raw = raw.strip()
        if not raw:
            return True
        cmd = raw.split()[0].lower().strip(",:;!/")
        rest = raw[len(raw.split()[0]):].strip()
        if cmd in ("quit", "exit", "q"):
            return False
        if cmd in ("help", "h"):
            for i in range(len(self.S["help"])):
                self.say_ui("help:{}".format(i), C_DIM)
            return True
        if cmd in ("setup", "set"):
            self.run_setup()
            return True
        if cmd == "up":
            self.bring_up()
            return True
        if cmd == "start" and rest:
            m = self.target(rest.split()[0])
            if not m:
                self.say("no member '{}'".format(rest), C_BLOCK)
                return True
            name = sessions.sname(m["name"])
            if name in sessions.list_sessions():
                self.say("{} already running".format(config.display(m)), C_DIM)
            else:
                sessions.launch(self.cfg, m, attach=False)
                self.say(("已启动 {}（后台）" if self.lang == "zh"
                          else "started {} (background)").format(config.display(m)), C_DIM)
            return True
        if cmd in ("brief", "briefing", "简报"):
            arg = rest.lower()
            if arg in ("on", "off"):
                self.brief_on = arg == "on"
                self._last_brief = 0
                self.say("briefing panel: {}".format(arg.upper() if arg == "on" else "off"), C_DIM)
            else:
                self.briefs = brief.collect(self.cfg, self.statuses)
                for l in brief.text_report(self.cfg, self.statuses).splitlines():
                    self.say(l, C_REPLY)
            return True
        if cmd == "watch":
            self.watch_traffic = rest.lower() != "off"
            self.say("agent↔agent traffic: {}".format(
                "ON" if self.watch_traffic else "off"), C_DIM)
            return True
        if cmd == "roster":
            for m in self.cfg["members"]:
                self.say("{:<10} {:<18} [{}]  {}".format(
                    config.display(m), m["role"], m["agent"], m.get("focus") or ""), C_DIM)
            return True
        if cmd == "standup":
            self.say(board.standup(self.cfg), 0)
            return True
        if cmd == "log":
            import subprocess  # reuse the CLI pretty-printer
            me = config.root() / "bin" / "myteam"
            r = subprocess.run([str(me), "log", "15"], capture_output=True, text=True)
            self.say(r.stdout.rstrip() or "no bus traffic yet", C_DIM)
            return True
        if cmd == "tasks":
            rows = board.listing()
            if not rows:
                self.say("no open tasks", C_DIM)
            for t in rows:
                self.say("#{:<3} [{:<10}] {:<8} {}".format(
                    t["id"], t["owner"][:10], t["status"], t["task"]), C_DIM)
            return True
        if cmd == "done" and rest:
            t = board.set_status(rest.split()[0], "done")
            self.say("✓ done: {}".format(t["task"]) if t else "no such task", C_DIM)
            return True
        if cmd == "assign" and rest:
            parts = rest.split(None, 1)
            m = self.target(parts[0]) if parts else None
            if m and len(parts) == 2:
                tid, note = board.assign(m["name"], parts[1].strip('"'), by="owner")
                self.awaiting[sessions.sname(m["name"])] = time.time()
                self.say("task #{} → {}{}".format(tid, config.display(m), note), C_PI)
            else:
                self.say("usage: assign <member> <task>", C_BLOCK)
            return True
        if cmd == "open" and rest:
            m = self.target(rest.split()[0])
            if m:
                name = sessions.sname(m["name"])
                if name not in sessions.list_sessions():
                    sessions.launch(self.cfg, m, attach=False)
                    self.say("(started {} — opening…)".format(config.display(m)), C_DIM)
                    time.sleep(1)
                curses.endwin()
                sessions.attach_to(name)
                self.scr.refresh()
                self.say_ui("back", C_DIM)
            else:
                self.say("no member '{}'".format(rest), C_BLOCK)
            return True
        # @mentions (several allowed) / "sam: text" / "sam, text"
        if raw.startswith("@"):
            words = raw.split()
            mentions, rest_words = [], []
            for i, w in enumerate(words):
                if w.startswith("@") and not rest_words:
                    mentions.append(w[1:].strip(",:;"))
                else:
                    rest_words = words[i:]
                    break
            text = " ".join(rest_words).strip()
            if not text:
                self.say("say something after the @mentions", C_BLOCK)
                return True
            targets = (self.cfg["members"] if any(t.lower() == "all" for t in mentions)
                       else [self.target(t) for t in mentions])
            seen = set()
            for m in targets:
                if m and m["name"] not in seen:
                    seen.add(m["name"])
                    self.send(m, text)
            bad = [t for t, m in zip(mentions, targets) if m is None]
            if bad and "all" not in [b.lower() for b in bad]:
                self.say("no member: {}".format(", ".join(bad)), C_BLOCK)
            return True
        from . import team
        if cmd in ("inbox", "staff"):
            self.say(team.inbox_text(self.cfg) if cmd == "inbox" else team.staff_text(self.cfg),
                     C_DIM)
            return True
        if cmd in ("approve", "decline") and rest:
            parts = rest.split(None, 1)
            self.say(team.decide(self.cfg, parts[0], cmd == "approve",
                                 parts[1] if len(parts) > 1 else ""), C_PI)
            return True
        mg = team.manager(self.cfg)
        first = raw.split()[0]
        m = self.target(cmd)
        if m and rest and (not mg or m["name"] == mg["name"] or first[-1] in ":,"):
            self.send(m, rest.lstrip(",:; "))
            return True
        if mg:                                   # everything else goes to the manager
            self.send(mg, raw)
            return True
        self.say_ui("notunderstood", C_BLOCK)
        return True

    # ---------- setup menu ----------
    def run_setup(self):
        from . import skills, wizard
        from .cli import cmd_edit, cmd_retire
        curses.endwin()
        lang_before = self.lang
        try:
            while True:
                print()
                menu = self.S["setup_menu"]
                print(menu[0].format(self.cfg["group"],))
                for line in menu[1:4]:
                    print(line)
                print(menu[4].format(lang_of(self.cfg)))
                print(menu[5])
                print(menu[6])
                print(menu[7])
                print(menu[8])
                choice = wizard.ask("choice", "0")
                if choice == "1":
                    wizard.hire(self.cfg)
                    config.save(self.cfg)
                    skills.sync(self.cfg)
                elif choice == "2":
                    name = wizard.ask(self.S["setup_which"])
                    if name:
                        try:
                            cmd_edit(self.cfg, name)
                        except SystemExit as e:
                            print(e)
                elif choice == "3":
                    name = wizard.ask(self.S["setup_which"])
                    if name:
                        try:
                            cmd_retire(self.cfg, name)
                        except SystemExit as e:
                            print(e)
                elif choice == "4":
                    v = wizard.ask(self.S["setup_lang"], "1")
                    self.cfg.setdefault("prefs", {})["lang"] = "zh" if v == "2" else "en"
                    config.save(self.cfg)
                    self.lang = lang_of(self.cfg)
                    self.S = S.get(self.lang, S["en"])
                elif choice == "7":
                    from . import packs
                    zh = self.lang == "zh"
                    cur = packs.of(self.cfg)["id"]
                    opts = ["{}{}".format(p["zh"] if zh else p["en"], "  ←" if p["id"] == cur else "")
                            for p in packs.PACKS]
                    j = wizard.choose("领域预设：" if zh else "field preset:", opts,
                                      default=[p["id"] for p in packs.PACKS].index(cur) + 1)
                    self.cfg["pack"] = packs.PACKS[j]["id"]
                    config.save(self.cfg)
                    skills.sync(self.cfg)
                    print(("✓ 已切换为 {}；现有成员保留原角色" if zh else
                           "✓ preset is now {}; existing members keep their roles").format(
                        packs.PACKS[j]["zh"] if zh else packs.PACKS[j]["en"]))
                elif choice == "6":
                    from . import profile
                    zh = self.lang == "zh"
                    print("（回车保留当前值；输入 - 清空）" if zh else
                          "(enter keeps the current value; type - to clear)")
                    pr = dict(profile.get(self.cfg))
                    for key, en, zhl, ph, _ml in profile.fields(self.cfg):
                        v = wizard.ask("{} — {}".format(zhl if zh else en, ph), pr.get(key, ""))
                        if v.strip() == "-":
                            pr.pop(key, None)
                        elif v.strip():
                            pr[key] = v.strip()
                    self.cfg["profile"] = pr
                    config.save(self.cfg)
                    skills.sync(self.cfg)
                    print("✓ 公司简介已保存" if zh else "✓ company profile saved — every member's skills updated")
                elif choice == "5":
                    n = skills.sync(self.cfg)
                    print("✓ {} skills x {} members".format(n, len(self.cfg["members"])))
                else:
                    break
        finally:
            self.cfg = config.load() or self.cfg
            self.lang = lang_of(self.cfg)
            self.S = S.get(self.lang, S["en"])
            self.scr.refresh()
            self.scr.clearok(True)
            if self.lang != lang_before:
                self.relocalize()
            self.say_ui("setup_done", C_DIM)

    # ---------- completion ----------
    def complete(self):
        words = self.input.split()
        if not words or self.input.endswith(" "):
            return
        last = words[-1]
        pool = [config.display(m) for m in self.cfg["members"]] + [
            "assign", "tasks", "done", "roster", "standup", "log", "watch",
            "open", "start", "up", "help", "quit", "setup", "set", "@all"]
        pool += ["@" + config.display(m) for m in self.cfg["members"]]
        hits = [p for p in pool if p.startswith(last)]
        if len(hits) == 1:
            words[-1] = hits[0]
            self.input = " ".join(words) + " "
        elif len(hits) > 1:
            self.say("… " + "  ".join(sorted(hits)), C_DIM)

    # ---------- drawing ----------
    def _side_width(self, w):
        need = max([cols(s.replace("{mgr}", self._mgr_name())) for s in self.S["sc_lines"]]
                   + [20]) + 3
        return max(20, min(34, need, w // 3))

    def _put(self, y, x, s, attr=0):
        try:
            self.scr.addstr(y, x, s, attr)
        except curses.error:
            pass  # bottom-right cell or a resize race — never crash the room

    def _draw_brief(self, x, width, h):
        """Pinned panel at the top of the feed. Returns the first free row."""
        scr = self.scr
        order = {"working": 0, "blocked": 1, "idle": 2, "gone": 3, "off": 4}
        glyphs = {"working": ("●", C_WORK), "blocked": ("◐", C_BLOCK),
                  "idle": ("○", C_OK), "off": ("·", C_DIM), "gone": ("✗", C_BLOCK)}
        rows = sorted(self.briefs, key=lambda r: order.get(r["status"], 9))
        active = [r for r in rows if r["status"] != "off" or r["doing"]]
        idle_off = [config.display(r["m"]) for r in rows
                    if r["status"] == "off" and not r["doing"]]
        cap = max(2, (h - 6) // 2)
        y = 1
        self._put(y, x, fit(self.S["brief"], width), curses.A_BOLD | curses.color_pair(C_REPLY))
        y += 1
        if not active:
            self._put(y, x, fit(self.S["brief_none"], width), curses.color_pair(C_DIM))
            y += 1
        for r in active[:cap]:
            m = r["m"]
            g, col = glyphs.get(r["status"], ("?", C_DIM))
            role = ROLE_ZH.get(m["role"], m["role"]) if self.lang == "zh" else m["role"]
            nm, rl = fit(config.display(m), 10), fit(role, 18)
            head = nm + " " * (11 - cols(nm)) + rl + " " * (20 - cols(rl))
            tail = ""
            if r["tasks"]:
                tail += "  [{}{}]".format(r["tasks"], " 任务" if self.lang == "zh" else " task")
            if r["ts"]:
                tail += "  " + brief.ago(r["ts"])
            doing = r["doing"] or ("—" if r["status"] != "off" else self.S["brief_off"])
            self._put(y, x, g, curses.color_pair(col))
            self._put(y, x + 2, fit(head, width - 2), curses.A_BOLD)
            room = width - 2 - cols(head)
            if room > 4:
                self._put(y, x + 2 + cols(head), fit(doing + tail, room))
            y += 1
        more = len(active) - cap
        rest = (["+{} more (`brief`)".format(more)] if more > 0 else []) + \
               (["{}: {}".format(self.S["brief_off"], ", ".join(idle_off))] if idle_off else [])
        if rest:
            self._put(y, x, fit("  " + " · ".join(rest), width), curses.color_pair(C_DIM))
            y += 1
        scr.hline(y, x - 1, curses.ACS_HLINE, width + 1)
        return y + 1

    def draw(self):
        scr = self.scr
        h, w = scr.getmaxyx()
        scr.erase()
        side = self._side_width(w)
        # title
        title = " {} — {} ".format(self.cfg["group"], self.S["room"])
        clock = time.strftime(" %H:%M:%S ")
        scr.attron(curses.color_pair(C_TITLE) | curses.A_BOLD)
        pad = max(1, w - 1 - cols(title) - cols(clock))
        self._put(0, 0, fit(title + " " * pad + clock, w - 1))
        scr.attroff(curses.color_pair(C_TITLE) | curses.A_BOLD)
        # sidebar
        glyphs = {"working": ("●", C_WORK), "blocked": ("◐", C_BLOCK),
                  "idle": ("○", C_OK), "off": ("·", C_DIM)}
        from . import team
        mg = team.manager(self.cfg)
        groups = ([(self.S["manager_hdr"], [mg]),
                   (self.S["spec_hdr"], team.specialists(self.cfg))] if mg
                  else [(self.S["members"], self.cfg["members"])])
        row = 1
        for hdr, ms in groups:
            if row >= h - 3:
                break
            scr.addnstr(row, 1, hdr, side - 2, curses.A_BOLD)
            row += 1
            for m in ms:
                st = self.statuses.get(m["name"], "off")
                g, col = glyphs[st]
                if row < h - 3:
                    star = "★ " if mg and m is mg else ""
                    scr.addnstr(row, 1, g, 2, curses.color_pair(col))
                    scr.addnstr(row, 3, fit(star + config.display(m), 14), side - 4,
                                curses.A_BOLD)
                    if st == "off" and mg and m is not mg:
                        st_lbl = self.S["asleep"]
                    elif self.lang == "zh":
                        st_lbl = STATUS_ZH.get(st, st)
                    else:
                        st_lbl = st
                    role_lbl = ROLE_ZH.get(m["role"], m["role"]) if self.lang == "zh" \
                        else m["role"]
                    scr.addnstr(row + 1, 3, "{} {}".format(st_lbl, role_lbl),
                                side - 4, curses.color_pair(C_DIM))
                    row += 2
            row += 1
        row -= 1
        if row < h - 3:
            need = len(team.pending_requests())
            scr.addnstr(row, 1, "{}: {}".format(self.S["needs_you"], need), side - 2,
                        curses.color_pair(C_BLOCK) | curses.A_BOLD if need
                        else curses.color_pair(C_DIM))
        if row < h - 3:
            q = sum(len(bus.pending(sessions.sname(m["name"])))
                    for m in self.cfg["members"])
            scr.addnstr(row + 1, 1, "{}: {}".format(self.S["queued"], q), side - 2,
                        curses.color_pair(C_DIM))
            open_t = len(board.listing())
            scr.addnstr(row + 2, 1, "{}: {}".format(self.S["opentasks"], open_t),
                        side - 2, curses.color_pair(C_DIM))
            y0 = row + 4
            if y0 < h - 4:
                scr.addnstr(y0, 1, self.S["shortcuts"], side - 2, curses.A_BOLD)
                for i, sc in enumerate(self.S["sc_lines"]):
                    if y0 + 1 + i < h - 3:
                        scr.addnstr(y0 + 1 + i, 1, sc.replace("{mgr}", self._mgr_name()),
                                    side - 2,
                                    curses.color_pair(C_DIM))
        for y in range(1, h - 2):
            scr.addch(y, side, curses.ACS_VLINE)
        # feed
        feed_w = w - side - 3
        y = 1
        if self.brief_on:
            y = self._draw_brief(side + 2, feed_w, h)
        feed_h = h - 3 - y
        visible = self.feed[-(feed_h + self.scroll):len(self.feed) - self.scroll
                            or None]
        visible = visible[-feed_h:] if feed_h > 0 else []
        for color, line, *_ in visible:
            attr = curses.color_pair(color) if color else 0
            self._put(y, side + 2, fit(line, feed_w), attr)
            y += 1
        # input + hints
        scr.hline(h - 3, 0, curses.ACS_HLINE, w)
        prompt = "you> "
        scr.addnstr(h - 2, 1, prompt, 5, curses.color_pair(C_PI) | curses.A_BOLD)
        shown = self.input[-(w - len(prompt) - 3):]
        scr.addnstr(h - 2, 1 + len(prompt), shown, w - len(prompt) - 2)
        hint = self.S["hint"].format("ON" if self.watch_traffic else "off")
        scr.attron(curses.color_pair(C_DIM))
        scr.addnstr(h - 1, 0, hint[:w - 1], w - 1)
        scr.attroff(curses.color_pair(C_DIM))
        scr.move(h - 2, min(w - 2, 1 + len(prompt) + len(shown)))
        scr.refresh()

    # ---------- main loop ----------
    def bring_up(self):
        """`up`: start every not-running member + the daemon in the background.
        tmux's server starts itself on the first session."""
        if not sessions.tmux_ok():
            self.say("needs tmux (conda install -c conda-forge tmux)", C_BLOCK)
            return
        live = sessions.list_sessions()
        started = []
        from . import team
        mg = team.manager(self.cfg)
        for m in ([mg] if mg else self.cfg["members"]):
            if sessions.sname(m["name"]) not in live:
                self.say(team.wake(self.cfg, m, by="owner"), C_DIM)
                started.append(config.display(m))
        me = config.root() / "bin" / "myteam"
        sessions.run_daemon_session('"{}" daemon run'.format(me))
        if started:
            self.say(("已在后台启动：{}（守护进程已运行）" if self.lang == "zh"
                      else "started in the background: {} (daemon running)"
                      ).format(", ".join(started)), C_DIM)
        else:
            self.say("已全部在运行" if self.lang == "zh"
                     else "everyone is already running", C_DIM)

    def run(self):
        curses.curs_set(1)
        self.scr.timeout(150)
        self.say_ui("welcome", C_DIM)
        self.say_ui("tip", C_DIM)
        while True:
            self.poll()
            self.draw()
            try:
                ch = self.scr.get_wch()
            except curses.error:
                continue
            if isinstance(ch, str) and ch.isprintable():
                self.input += ch
                self.hist_i = None
            elif ch in ("\n", "\r", curses.KEY_ENTER, 10, 13):
                line = self.input
                self.input = ""
                if line.strip():
                    self.history.append(line)
                self.scroll = 0
                if not self.handle(line):
                    return
            elif ch in (curses.KEY_BACKSPACE, "\x7f", "\b", 127, 8):
                self.input = self.input[:-1]
            elif ch == "\t":
                self.complete()
            elif ch == curses.KEY_UP:
                if self.history:
                    self.hist_i = (len(self.history) - 1 if self.hist_i is None
                                   else max(0, self.hist_i - 1))
                    self.input = self.history[self.hist_i]
            elif ch == curses.KEY_DOWN:
                if self.history and self.hist_i is not None:
                    self.hist_i += 1
                    if self.hist_i >= len(self.history):
                        self.hist_i = None
                        self.input = ""
                    else:
                        self.input = self.history[self.hist_i]
            elif ch == curses.KEY_PPAGE:
                self.scroll = min(len(self.feed), self.scroll + 5)
            elif ch == curses.KEY_NPAGE:
                self.scroll = max(0, self.scroll - 5)
            elif ch == curses.KEY_F5:
                self.scr.clearok(True)
            elif ch == curses.KEY_RESIZE:
                pass  # next draw() picks up the new size


def _main(stdscr, cfg):
    curses.start_color()
    curses.use_default_colors()
    pairs = [(C_TITLE, curses.COLOR_BLACK, curses.COLOR_CYAN),
             (C_OK, curses.COLOR_GREEN, -1),
             (C_WORK, curses.COLOR_GREEN, -1),
             (C_BLOCK, curses.COLOR_YELLOW, -1),
             (C_DIM, curses.COLOR_BLUE, -1),
             (C_PI, curses.COLOR_MAGENTA, -1),
             (C_TRAFFIC, curses.COLOR_CYAN, -1),
             (C_REPLY, curses.COLOR_WHITE, -1)]
    for pid, fg, bg in pairs:
        try:
            curses.init_pair(pid, fg, bg)
        except curses.error:
            pass
    Room(stdscr, cfg).run()


def room(cfg):
    """Entry point. Returns 0, or raises for the caller to fall back."""
    curses.wrapper(_main, cfg)
    print(S.get(lang_of(config.load() or cfg), S["en"])["left"])
    return 0
