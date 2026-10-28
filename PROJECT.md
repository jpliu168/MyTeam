# MyTeam — project state & decisions (portable source of truth)

- **Owner:** Paul Liu (jpliu@ncsu.edu).
- **What:** MyLab forked for small businesses / one-person companies. Same
  core (tmux sessions, bus, board, daemon, control-room TUI, skills
  renderer); business roles, vocabulary and skills.
- **Folder:** `/Users/jpliu/agents/MyTeam/` (command `myteam`), state in
  `~/myteam/`, tmux prefix `myteam-`, env `MYTEAM_*`. MyLab untouched.
- **Created:** 2026-10-16 as a separate copy (Paul's choice) — core fixes
  must be applied to both MyLab and MyTeam.

## Differences from MyLab
- Roles: operations-manager, executive-assistant, bookkeeper, tax-prep,
  customer-support, sales, marketing, copywriter, market-researcher,
  contracts-compliance, hr, data-analyst, reviewer, generalist.
- Skills: team-collab, house-style (business voice), customer-replies,
  money-records (replaces fetch-paper), make-slides (business decks).
- Vocabulary: PI → owner (prompt `you>`, bus sender "owner"), lab → team,
  实验室 → 团队; handbook seeded with business files (pricing, policies,
  voice, FAQ, approved replies, chart of accounts).
- Hard rule: agents draft/prepare; owner sends, signs, pays, files.
- Fixes applied here first (not yet in MyLab): standup skips dotfiles
  (.DS_Store); sidebar width fits the shortcut text; member names up to 12
  chars in the sidebar; `office` banner uses the team name, not "Liu Lab".

## Briefing (added 2026-10-16)
- Pinned panel at the top of the control-room feed: one line per member —
  status, role, what they're doing, open tasks, age. `brief` prints the full
  briefing into the feed; `brief on|off` toggles the panel; `myteam brief`
  from any shell.
- Source order (lib/myteam/brief.py): member's own note (`myteam now "..."`,
  members/<name>/NOW.json, fresh < 6h) → Claude Code's tmux pane title →
  newest open task → last bus message. team-collab skill tells members to
  keep `myteam now` current.
- Also fixed: title bar/feed now measure CJK width (stray clock digit gone).

## Web control room (added 2026-10-16)
- `myteam-web` (bin/myteam-web → lib/myteam/web.py, page in lib/myteam/webui/index.html).
  stdlib ThreadingHTTPServer on 127.0.0.1 (port 8765+), per-run token
  (?t= → HttpOnly SameSite cookie), Host-header check, files limited to
  deliverables/ + handbook/. web.json in ~/myteam/ makes a second launch reopen
  the same server. Background Hub thread mirrors the TUI poller.
- Page: members sidebar, briefing, feed + composer (same command language),
  Tasks/Files tabs, member terminal drawer (live tail + owner keystrokes:
  Send+Enter, Enter, ↑↓, Esc; Start/Stop), EN/中文 toggle, light/dark, phone layout.
- Replies (TUI + web) now start after the injected "[myteam …]" line.

## Setup in the web + company profile (added 2026-10-16)
- ⚙ Setup drawer: team name, language, hire/edit/retire (archive only), re-render
  skills. Chinese-only names get an internal key member-N; display stays as typed.
- Company profile (lib/myteam/profile.py, 16 fields: business, industry, entity,
  location, products, customers, pricing, voice, goals, owner's rules …) in
  config.json "profile" → rendered into every member as the `company-profile`
  skill + handbook/company-profile.md. Also TUI setup option 6.

## Field presets (added 2026-10-17)
- lib/myteam/packs.py: business, research, teaching, nonprofit, freelance —
  boss word ({{BOSS}}: owner/PI/instructor/director), unit ({{UNIT}}), skill
  map (render-name → skills/<dir>), handbook starter. cfg["pack"], default business.
- roles.py: BY_PACK libraries + ZH labels; by_id() prefers the team's preset.
- profile.py: per-preset fields; skill/handbook name per preset
  (company-/lab-/course-/organization-/practice-profile).
- skills.sync renders only the preset's skills, keeps a manifest
  (.claude/skills/.myteam-generated.json) and removes stale generated ones.
- New skills: house-style-{research,teaching,nonprofit}, fetch-paper,
  make-slides-{research,teaching}, student-privacy, course-materials, donor-care.
- First-run wizard asks the preset; TUI setup 7; web Setup "Field preset"
  select; hire form groups roles by preset (★ = current).

## Open / next
- Port the three fixes above back to MyLab.
- Customer support can only draft; a real inbox/helpdesk connection would be
  a later, owner-approved step.
- Same open items as MyLab: status regexes, no per-agent resume.

## Team tables — `myteam db` (added 2026-10-20)
- lib/myteam/db.py, stdlib sqlite3 + FTS5; one file `~/myteam/data/team.db`. Free-form
  JSON fields per record; tables: tables / records / aliases / changes / search(fts5).
- Identity: key fields (openalex_id, orcid, email, homepage, website, linkedin, url; per-table
  `--keys`) else name+organization → re-adding upserts, empty values never erase, a conflicting
  ID is kept + flagged, name variants go to `other_names`, every fact keeps `source` URLs.
- Agents add/set/verify/mark status; only the owner `remove`s (soft). `stale`, `history`,
  `export` (→ deliverables/data/<table>.csv, UTF-8 BOM for Excel), read-only `sql`.
- Common skill `skills/team-data` in every preset. Not yet in MyLab.

## Profiles + Research Admin preset (added 2026-10-21)
- Several independent teams on one computer (Paul: typically 2–3), e.g. `research-pi`
  (lab for a PI) and `research-admin` (research office for a director).
  `myteam list` · `myteam use <name>` (new name → created, setup wizard runs with the preset
  guessed from the name) · `myteam -p <name> <cmd>` one-off. In the control room: `list`, `use <name>`.
- lib/myteam/profiles.py. Default profile = `~/myteam` (unchanged, tmux prefix `myteam-`);
  others = `~/myteam/profiles/<name>/`, tmux prefix `myteam_<name>-` so profiles never see each
  other's sessions and can run at the same time. Registry `~/myteam/profiles.json`
  (active + paths). Resolution: MYTEAM_PROFILE → MYTEAM_STATE → MYTEAM_SESSION name → active.
  Member sessions and the daemon are started with MYTEAM_PROFILE/MYTEAM_STATE pinned.
- New preset `research-admin` (boss: director, unit: research office): chief-of-staff (manager),
  funding-scout, expert-curator, proposal-coordinator, development-writer, communications
  (news releases + social media), events-training, research-analyst, compliance-awards,
  reviewer, generalist. New skills: funding-search (`opportunities` table + weekly digest),
  expert-database (`experts` table, public professional info only), house-style-research-admin.
  Office-profile form fields in profile.py.
- Backup of the files changed: _backup-20261021-profiles/.
- Next: profile switcher in the web control room (today each profile runs its own `myteam-web`:
  `myteam -p research-admin web`); port profiles to MyLab if wanted.

## Fixes 2026-10-21/22
- Profiles moved under `~/myteam/profiles/<name>/`; registry `~/myteam/profiles.json`.
- Claude Code's folder-trust menu now defaults to "No, exit": `team._trust_yes` moves the
  cursor to "Yes, I trust this folder" (uses web.find_menu/choose) before Enter.
- If a member quits right after starting, its last screen is saved to
  members/<name>/last-exit.log and shown in the "exited right after starting" message.
- Sidebar (web + TUI) and `myteam list`: Manager · Specialists · "<manager> can bring in" roles.
- Web composer hint/welcome use the real manager name; voice input (browser Web Speech API,
  mic button, en-US / zh-CN, never auto-sends).
- Full replies: `sessions.reply_of` reads the answer from Claude Code's transcript
  (~/.claude/projects/<cwd with non-alphanumerics as '-'>/*.jsonl, final text after the last
  tool result); falls back to tmux screen + scrollback for other CLIs. Used by web, TUI, bus.ask.

## Academic Admin preset (added 2026-10-26)
- New 7th preset `academic-admin`: "University academic leadership (dean / department head)",
  boss "dean/head", unit "college or department". 12 roles: chief-of-staff (manager),
  faculty-affairs, curriculum-scheduling, student-programs, budget-planning,
  assessment-accreditation, metrics-analyst, governance-committees, advancement-alumni,
  communications, reviewer, generalist (ACADEMIC_ADMIN in roles.py, with zh names).
- New skills: house-style-academic-admin, confidential-records (personnel + FERPA rules; no
  ranking candidates, no P&T recommendations, aggregates only in shared outputs).
- Unit-profile form (16 fields) in profile.py; handbook starter in packs.py; profile-name
  hints (academic, dean, chair, head, dept, department, college, provost) in profiles.py;
  setup menu text in tui.py (en + zh).
- Backup of the files changed: _backup-20261026-academic-admin/.

## Graduate Student preset + News watcher (added 2026-10-27)
- New 8th preset `graduate`: "Graduate student (MS / PhD)", boss "grad student", unit
  "graduate work". 15 roles (GRADUATE in roles.py, zh names): chief-of-staff (manager),
  research-assistant, lit-reader (`papers` db table + refs.bib), coursework-coach (learns, never
  does graded work), thesis-writer, manuscript-writer, data-analyst, lab-life, milestones-forms,
  fellowships-career (`funding` table), slides-maker, ta-helper, reviewer, news-watch, generalist.
- New skills: house-style-graduate, academic-integrity (course AI policy, data/citation honesty,
  authorship, ai-use log in deliverables/plan/ai-use.md). Also gets student-privacy (TA work).
- Student-profile form (16 fields) in profile.py; handbook starter in packs.py (program, advisor,
  projects, courses, lab, cv, news-sources, style); name hints (grad, graduate, phd, student,
  thesis, dissertation, masters, ms) checked first in profiles.py; setup menu text in tui.py.
- New shared role `news-watch` (NEWS_WATCH in roles.py), also added to research,
  research-admin and academic-admin: collects public team/lab/field news into a `news` db table
  and deliverables/news/<YYYY-WW>.md. Sources: what the boss forwards (LinkedIn notification
  emails, pasted posts), public pages without login, handbook/news-sources.md watch list.
  Never logs in to LinkedIn/social accounts, never uses the boss's cookies, never scrapes,
  never posts/likes/connects. research handbook also lists news-sources.md.

