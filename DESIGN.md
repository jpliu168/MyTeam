# MyTeam design — manager-led team (v0.2)

Agreed 2026-10-19. This is the plan the code is built against.

## Why MyTeam (vs. talking to Claude Code / Codex directly)

For a single task, a raw agent is as good or better. MyTeam is not a better
agent; it is **the office around the agents**:

1. **Knows the organization** — handbook, profile, the boss's preferences.
2. **Keeps learning** — preferences, experience notes and team skills are
   written down and read back, so the team gets better at *this* org's work.
3. **Accountability** — one place that says what's done, stuck, and waiting
   on the boss.
4. **Works while the boss is away**, and runs standing routines.
5. **Second opinions and approval gates** built in.
6. **Usable by non-coders** — talk to one manager, in a terminal or browser.

Test for every feature: *would this be just as good with one Claude Code
window open?* If yes, it is not MyTeam's job.

## People

- **The boss** (owner / PI / instructor / director) talks to **one named
  manager** only. Plain text in the control room or web goes to the manager.
- **The manager** is a full agent session with the preset's manager role
  (operations-manager, chief-of-staff, course-manager, studio-manager).
- **Specialists** have no names — a role + focus (bookkeeper,
  writer-grants, lit-scout). Each has a persistent folder
  (`members/<id>/`) with its NOTEBOOK.md, so knowledge accumulates even
  though the specialist only runs while there is work. Nicknames optional.
- The boss can still look in on (`open`) or `@mention` a specialist —
  an advanced path, never required.

## What the manager may do alone vs. must ask

Alone (logged, mentioned in the summary):
- add a specialist from the preset's role catalog (`myteam add`)
- wake / sleep specialists (`myteam wake`, `myteam sleep`), within the
  concurrency cap (default 3 running specialists)
- pick which installed agent CLI runs a job

Must file a request the boss approves (`myteam request` → boss `inbox`,
`approve`, `decline`):
- any folder outside ~/myteam (the security boundary)
- money, accounts, paid services, anything public or sent outside
- custom roles not in the catalog (unless autonomy = full)
- removing a specialist

Setting `prefs.autonomy`: `ask` (manager only proposes) · `catalog`
(default) · `full` (everything except folders and money).

## Agent CLIs

- **Claude Code is the default and the only requirement.**
- Codex and Gemini CLI are optional. If installed (and `prefs.other_clis`
  is on), the manager *may* pick them per job (`myteam wake <s> --cli codex`),
  guided by `handbook/routing.md`. It never has to.
- If an optional CLI is missing, fails, or is stuck at a login prompt, the
  job falls back to Claude Code automatically and the summary says so.
- Each CLI gets the right folder flags (`--add-dir` / `--include-directories`),
  auto-edit mode (`prefs.auto_edits`, default on: edits inside the allowed
  folders don't need approval), and its instruction file
  (`.claude/skills/`, `AGENTS.md`, `GEMINI.md`).

## Work loop

boss → manager: goal
manager: plan → add/wake 1–3 specialists → `myteam assign` tasks
specialists: work → outputs in deliverables/ → `myteam report "…"` → manager
manager: check / send to reviewer → one summary to the boss, with
"needs your decision" items → sleep idle specialists

## Learning loop (the core of "gets better every week")

Agents don't learn by themselves; the team learns by writing down and reading back.

| what | where | who writes |
|---|---|---|
| boss's preferences & corrections | `handbook/preferences.md` | manager, when the boss corrects anything |
| experience notes | `members/<id>/NOTEBOOK.md` | each specialist, after each job |
| team skills (repeatable procedures) | `~/myteam/skills/<name>/SKILL.md` | manager / specialists, when a job type repeats 2–3× |
| learning log | `handbook/learning-log.md` (`myteam learned "…"`) | anyone who changes the above |

Every Monday the daemon asks the manager to tidy notes (merge, prune,
fix) and include **"What we learned this week"** in its summary; the boss
can veto any item. Customer / student / donor personal data never goes
into skills or notebooks.

## Build order

1. ✅ manager + unnamed specialists, add / wake / sleep / report, cap
2. ✅ boss inbox: requests, approvals, blocked members
3. ✅ learning loop files, learned skills rendered to everyone, weekly tidy nudge
4. ✅ CLI adapters (Claude default; Codex, Gemini optional) + fallback
5. ⏳ routines (weekly scans, month-end close…) via the daemon
6. ⏳ web UI: inbox panel, manager-first layout
